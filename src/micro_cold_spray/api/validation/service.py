from typing import Dict, Any, List
from datetime import datetime

from ..base import BaseService
from ...core.infrastructure.config.config_manager import ConfigManager
from ...core.infrastructure.messaging.message_broker import MessageBroker

class ValidationError(Exception):
    def __init__(self, message: str, context: Dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context if context is not None else {}

class ValidationService(BaseService):
    def __init__(
        self,
        config_manager: ConfigManager,
        message_broker: MessageBroker
    ):
        super().__init__(service_name="validation")
        self._config_manager = config_manager
        self._message_broker = message_broker
        self._validation_rules = {}
        
    async def start(self) -> None:
        """Initialize validation service."""
        await super().start()
        
        # Load validation rules
        config = await self._config_manager.get_config("process")
        self._validation_rules = config["process"]["validation"]
        
        # Subscribe to validation requests
        await self._message_broker.subscribe(
            "validation/request",
            self._handle_validation_request
        )
        
    async def _handle_validation_request(self, data: Dict[str, Any]) -> None:
        """Handle validation request."""
        try:
            validation_type = data["type"]
            validation_data = data["data"]
            
            # Validate based on type
            if validation_type == "parameters":
                result = await self._validate_parameters(validation_data)
            elif validation_type == "pattern":
                result = await self._validate_pattern(validation_data)
            elif validation_type == "sequence":
                result = await self._validate_sequence(validation_data)
            elif validation_type == "safety":
                result = await self._validate_safety_conditions(validation_data)
            elif validation_type == "hardware":
                result = await self._validate_hardware_set(validation_data)
            elif validation_type == "material":
                result = await self._validate_material(validation_data)
            elif validation_type == "process":
                result = await self._validate_process_conditions(validation_data)
            elif validation_type == "state":
                result = await self._validate_state_conditions(validation_data)
            else:
                raise ValidationError(f"Unknown validation type: {validation_type}")
                
            # Send validation response
            await self._message_broker.publish(
                "validation/response",
                {
                    "request_id": data.get("request_id"),
                    "type": validation_type,
                    "valid": result["valid"],
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            await self._message_broker.publish(
                "validation/response",
                {
                    "request_id": data.get("request_id"),
                    "type": data.get("type"),
                    "valid": False,
                    "errors": [str(e)],
                    "timestamp": datetime.now().isoformat()
                }
            ) 

    async def _validate_parameters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate process parameters."""
        errors = []
        warnings = []
        
        try:
            # Check required fields
            required = self._validation_rules["parameters"]["required_fields"]
            for field in required["fields"]:
                if field not in data:
                    errors.append(f"Missing required field: {field}")

            # Validate gas settings
            if "gas_flows" in data:
                gas_errors = await self._validate_gas_parameters(data["gas_flows"])
                errors.extend(gas_errors)

            # Validate powder feed settings
            if "powder_feed" in data:
                feed_errors = await self._validate_powder_feed(data["powder_feed"])
                errors.extend(feed_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            raise ValidationError("Parameter validation failed", {"error": str(e)})

    async def _validate_pattern(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern definition."""
        errors = []
        warnings = []
        
        try:
            pattern_type = data.get("type")
            if not pattern_type:
                errors.append("Pattern type not specified")
                return {"valid": False, "errors": errors}

            # Get pattern validation rules
            rules = self._validation_rules["patterns"]
            
            # Validate pattern bounds
            if "limits" in rules:
                bound_errors = await self._validate_pattern_bounds(
                    data,
                    rules["limits"]
                )
                errors.extend(bound_errors)

            # Validate type-specific parameters
            if pattern_type == "serpentine":
                type_errors = await self._validate_serpentine_pattern(data)
                errors.extend(type_errors)
            elif pattern_type == "spiral":
                type_errors = await self._validate_spiral_pattern(data)
                errors.extend(type_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            raise ValidationError("Pattern validation failed", {"error": str(e)})

    async def _validate_sequence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence definition."""
        errors = []
        warnings = []
        
        try:
            # Check required fields
            required = self._validation_rules["sequences"]["required_fields"]
            for field in required["fields"]:
                if field not in data:
                    errors.append(f"Missing required field: {field}")

            # Validate steps
            if "steps" in data:
                for i, step in enumerate(data["steps"]):
                    step_errors = await self._validate_sequence_step(step)
                    errors.extend([f"Step {i+1}: {err}" for err in step_errors])

            # Validate safety conditions
            if "safety" in self._validation_rules["sequences"]:
                safety_errors = await self._validate_safety_conditions(data)
                errors.extend(safety_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            raise ValidationError("Sequence validation failed", {"error": str(e)})

    async def _validate_safety_conditions(self, data: Dict[str, Any]) -> List[str]:
        """Validate safety conditions."""
        errors = []
        
        try:
            rules = self._validation_rules["sequences"]["safety"]
            
            # Check chamber pressure
            if "chamber_pressure" in rules:
                if not await self._check_chamber_pressure():
                    errors.append(rules["chamber_pressure"]["message"])

            # Check gas pressures
            if "gas_pressure" in rules:
                if not await self._check_gas_pressures():
                    errors.append(rules["gas_pressure"]["message"])

            # Check motion limits
            if "safe_position" in rules:
                if not await self._check_safe_position():
                    errors.append(rules["safe_position"]["message"])

            return errors

        except Exception as e:
            raise ValidationError("Safety validation failed", {"error": str(e)})

    async def get_rules(self, rule_type: str) -> Dict[str, Any]:
        """Get validation rules for specified type."""
        if rule_type not in self._validation_rules:
            raise ValidationError(f"Unknown rule type: {rule_type}")
        return self._validation_rules[rule_type] 

    async def _validate_gas_parameters(self, gas_data: Dict[str, Any]) -> List[str]:
        """Validate gas flow parameters."""
        errors = []
        try:
            # Get gas validation rules
            rules = self._validation_rules["parameters"]["gas_flows"]
            
            # Validate gas type
            if "gas_type" not in gas_data:
                errors.append("Gas type not specified")
            elif gas_data["gas_type"] not in rules["gas_type"]["choices"]:
                errors.append(f"Invalid gas type: {gas_data['gas_type']}")
                
            # Validate flow rates
            if "main_gas" in gas_data:
                flow = gas_data["main_gas"]
                if flow < rules["main_gas"]["min"] or flow > rules["main_gas"]["max"]:
                    errors.append(f"Main gas flow {flow} outside limits")
                    
            if "feeder_gas" in gas_data:
                flow = gas_data["feeder_gas"]
                if flow < rules["feeder_gas"]["min"] or flow > rules["feeder_gas"]["max"]:
                    errors.append(f"Feeder gas flow {flow} outside limits")
                    
        except Exception as e:
            errors.append(f"Gas parameter validation error: {str(e)}")
        return errors

    async def _validate_powder_feed(self, feed_data: Dict[str, Any]) -> List[str]:
        """Validate powder feed parameters."""
        errors = []
        try:
            rules = self._validation_rules["parameters"]["powder_feed"]
            
            # Validate frequency
            if "frequency" in feed_data:
                freq = feed_data["frequency"]
                if freq < rules["frequency"]["min"] or freq > rules["frequency"]["max"]:
                    errors.append(f"Frequency {freq} outside limits")
                    
            # Validate deagglomerator
            if "deagglomerator" in feed_data:
                deagg = feed_data["deagglomerator"]
                if "speed" not in deagg:
                    errors.append("Deagglomerator speed not specified")
                elif deagg["speed"] not in rules["deagglomerator"]["speed"]["choices"]:
                    errors.append(f"Invalid deagglomerator speed: {deagg['speed']}")
                    
        except Exception as e:
            errors.append(f"Powder feed validation error: {str(e)}")
        return errors

    async def _validate_sequence_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate sequence step."""
        errors = []
        try:
            rules = self._validation_rules["sequences"]["step_fields"]
            
            # Check required fields
            for field in rules["required_fields"]["fields"]:
                if field not in step:
                    errors.append(f"Missing required field: {field}")
                    
            # Check for unknown fields
            for field in step:
                if field not in rules["required_fields"]["fields"] + rules["optional_fields"]["fields"]:
                    errors.append(f"Unknown field: {field}")
                    
            # Validate step type-specific fields
            if "action" in step:
                action_errors = await self._validate_action_step(step)
                errors.extend(action_errors)
            elif "pattern" in step:
                pattern_errors = await self._validate_pattern_step(step)
                errors.extend(pattern_errors)
                
        except Exception as e:
            errors.append(f"Step validation error: {str(e)}")
        return errors

    async def _validate_pattern_bounds(self, pattern: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """Validate pattern bounds against stage limits."""
        errors = []
        try:
            # Get stage dimensions from hardware config
            hw_config = await self._config_manager.get_config("hardware")
            stage = hw_config["hardware"]["physical"]["stage"]["dimensions"]
            
            # Calculate pattern bounds
            bounds = await self._calculate_pattern_bounds(pattern)
            
            # Check X limits
            if bounds["min_x"] < 0 or bounds["max_x"] > stage["x"]:
                errors.append(rules["position"]["message"])
                
            # Check Y limits
            if bounds["min_y"] < 0 or bounds["max_y"] > stage["y"]:
                errors.append(rules["position"]["message"])
                
            # Check Z limits
            if bounds["min_z"] < 0 or bounds["max_z"] > stage["z"]:
                errors.append(rules["position"]["message"])
                
            # Check speed limits if specified
            if "speed" in pattern:
                speed = pattern["speed"]
                if speed > hw_config["hardware"]["safety"]["motion"]["max_speed"]:
                    errors.append(rules["speed"]["message"])
                    
        except Exception as e:
            errors.append(f"Pattern bounds validation error: {str(e)}")
        return errors

    async def _check_chamber_pressure(self) -> bool:
        """Check if chamber pressure is within limits."""
        try:
            # Get current pressure from Communication API
            response = await self._message_broker.request(
                "tag/request",
                {"tag": "pressure.chamber_pressure"}
            )
            pressure = response["value"]
            
            # Get pressure limits
            rules = self._validation_rules["states"]["chamber_vacuum"]["checks"][0]
            
            return pressure <= rules["value"]
            
        except Exception:
            return False

    async def _check_gas_pressures(self) -> bool:
        """Check if gas pressures are within limits."""
        try:
            # Get current pressures
            main_pressure = await self._get_tag_value("pressure.main_supply_pressure")
            reg_pressure = await self._get_tag_value("pressure.regulator_pressure")
            
            # Get pressure rules
            rules = self._validation_rules["validation"]["gas_pressure"]
            
            return main_pressure >= reg_pressure + rules["min_margin"]
            
        except Exception:
            return False

    async def _check_safe_position(self) -> bool:
        """Check if at safe position."""
        try:
            z_pos = await self._get_tag_value("motion.position.z_position")
            safe_z = await self._get_tag_value("safety.safe_z")
            
            return z_pos >= safe_z
            
        except Exception:
            return False

    async def _validate_hardware_set(self, data: Dict[str, Any]) -> List[str]:
        """Validate hardware set configuration."""
        errors = []
        try:
            rules = self._validation_rules["hardware"]
            
            # Check active set matches nozzle
            if "active_set" in rules:
                if not await self._validate_feeder_nozzle_match(data):
                    errors.append(rules["active_set"]["message"])
                    
            # Check position for set change
            if "set_change" in rules:
                if not await self._validate_trough_position():
                    errors.append(rules["set_change"]["message"])
                    
            # Check required fields
            if "required_fields" in rules:
                for field in rules["required_fields"]["fields"]:
                    if field not in data:
                        errors.append(f"Missing required field: {field}")
                        
            # Check for unknown fields
            if "optional_fields" in rules:
                valid_fields = rules["required_fields"]["fields"] + rules["optional_fields"]["fields"]
                for field in data:
                    if field not in valid_fields:
                        errors.append(f"Unknown field: {field}")
                        
        except Exception as e:
            errors.append(f"Hardware validation error: {str(e)}")
        return errors

    async def _validate_material(self, data: Dict[str, Any]) -> List[str]:
        """Validate material configuration."""
        errors = []
        try:
            rules = self._validation_rules["parameters"]["material"]
            
            # Check required fields
            if "required_fields" in rules:
                for field in rules["required_fields"]["fields"]:
                    if field not in data:
                        errors.append(f"Missing required field: {field}")
                        
            # Check for unknown fields
            if "optional_fields" in rules:
                valid_fields = rules["required_fields"]["fields"] + rules["optional_fields"]["fields"]
                for field in data:
                    if field not in valid_fields:
                        errors.append(f"Unknown field: {field}")
                        
        except Exception as e:
            errors.append(f"Material validation error: {str(e)}")
        return errors

    async def _validate_process_conditions(self, data: Dict[str, Any]) -> List[str]:
        """Validate process operating conditions."""
        errors = []
        try:
            rules = self._validation_rules["parameters"]["process"]
            
            # Check chamber pressure
            if "chamber_pressure" in rules:
                if not await self._check_chamber_pressure():
                    errors.append(rules["chamber_pressure"]["message"])
                    
            # Check feeder operation
            if "feeder_operation" in rules:
                for rule in rules["feeder_operation"]:
                    if not await self._check_feeder_operation(rule):
                        errors.append(rule["message"])
                    
            # Check flow stability
            if "flow_stability" in rules:
                for rule in rules["flow_stability"]:
                    if not await self._check_flow_stability(rule):
                        errors.append(rule["message"])
                    
            # Check gas pressure
            if "gas_pressure" in rules:
                if not await self._check_gas_pressures():
                    errors.append(rules["gas_pressure"]["message"])
                    
        except Exception as e:
            errors.append(f"Process condition validation error: {str(e)}")
        return errors

    async def _validate_state_conditions(self, state: str) -> List[str]:
        """Validate state transition conditions."""
        errors = []
        try:
            rules = self._validation_rules["states"]
            
            if state in rules:
                state_rules = rules[state]
                
                # Check chamber vacuum
                if "chamber_vacuum" in state_rules:
                    for check in state_rules["chamber_vacuum"]["checks"]:
                        if not await self._check_condition(check):
                            errors.append(check["error"])
                            
                # Check feeder operation
                if "feeder_operation" in state_rules:
                    for check in state_rules["feeder_operation"]["checks"]:
                        if not await self._check_condition(check):
                            errors.append(check["error"])
                            
                # Check gas flow stability
                if "gas_flow_stable" in state_rules:
                    for check in state_rules["gas_flow_stable"]["checks"]:
                        if not await self._check_condition(check):
                            errors.append(check["error"])
                            
                # Check safe position
                if "safe_position" in state_rules:
                    for check in state_rules["safe_position"]["checks"]:
                        if not await self._check_condition(check):
                            errors.append(check["error"])
                            
        except Exception as e:
            errors.append(f"State validation error: {str(e)}")
        return errors

    async def _get_tag_value(self, tag: str) -> Any:
        """Get tag value from Communication API."""
        try:
            response = await self._message_broker.request(
                "tag/request",
                {"tag": tag}
            )
            return response["value"]
        except Exception:
            raise ValidationError(f"Failed to get tag value: {tag}")

    async def _check_condition(self, check: Dict[str, Any]) -> bool:
        """Check a validation condition."""
        try:
            # Get current value
            value = await self._get_tag_value(check["tag"])
            
            # Check condition type
            if check.get("condition") == "less_than":
                return value < check["value"]
            elif check.get("condition") == "greater_than":
                return value > check["value"]
            elif check.get("condition") == "greater_than_equal":
                return value >= check["value"]
            elif check.get("condition") == "compare_to":
                target = await self._get_tag_value(check["compare_to"])
                tolerance = check.get("tolerance", 0)
                return abs(value - target) <= tolerance
            
            return False
            
        except Exception:
            return False

    async def _check_feeder_operation(self, rule: Dict[str, Any]) -> bool:
        """Check feeder operation conditions."""
        try:
            powder_feed = await self._get_tag_value("hardware_sets.feeder_control")
            feeder_flow = await self._get_tag_value("gas_control.feeder_flow.measured")
            
            # Check if feeder is running with low flow
            if powder_feed and feeder_flow < 2.0:
                return False
            
            return True
            
        except Exception:
            return False

    async def _check_flow_stability(self, rule: Dict[str, Any]) -> bool:
        """Check gas flow stability."""
        try:
            main_flow = await self._get_tag_value("gas_control.main_flow.measured")
            feeder_flow = await self._get_tag_value("gas_control.feeder_flow.measured")
            
            main_setpoint = await self._get_tag_value("gas_control.main_flow.setpoint")
            feeder_setpoint = await self._get_tag_value("gas_control.feeder_flow.setpoint")
            
            # Check flow stability
            main_stable = abs(main_flow - main_setpoint) <= 2.0
            feeder_stable = abs(feeder_flow - feeder_setpoint) <= 0.5
            
            return main_stable and feeder_stable
            
        except Exception:
            return False

    async def _validate_serpentine_pattern(self, data: Dict[str, Any]) -> List[str]:
        """Validate serpentine pattern parameters."""
        errors = []
        try:
            rules = self._validation_rules["patterns"]["serpentine"]
            params = data.get("params", {})
            
            # Check required parameters
            for field in rules["required_fields"]["fields"]:
                if field not in params:
                    errors.append(f"Missing required parameter: {field}")
                    
            # Validate parameter values
            if "length" in params and params["length"] <= 0:
                errors.append("Length must be positive")
            if "spacing" in params and params["spacing"] <= 0:
                errors.append("Spacing must be positive")
                
        except Exception as e:
            errors.append(f"Serpentine pattern validation error: {str(e)}")
        return errors

    async def _calculate_pattern_bounds(self, pattern: Dict[str, Any]) -> Dict[str, float]:
        """Calculate pattern bounds based on type."""
        pattern_type = pattern.get("type")
        params = pattern.get("params", {})
        
        if pattern_type == "serpentine":
            return {
                "min_x": 0,
                "max_x": params.get("length", 0),
                "min_y": 0,
                "max_y": params.get("width", 0),
                "min_z": 0,
                "max_z": 0
            }
        # Add other pattern types...
        
        return {
            "min_x": 0, "max_x": 0,
            "min_y": 0, "max_y": 0,
            "min_z": 0, "max_z": 0
        }
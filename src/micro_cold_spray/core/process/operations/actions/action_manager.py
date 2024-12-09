"""Action management component."""
from datetime import datetime
from typing import Dict, Any

from loguru import logger

from ....exceptions import ConfigurationError, OperationError, ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker


class ActionManager:
    """Manages execution of atomic actions and action groups."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ) -> None:
        """Initialize action manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._atomic_actions = {}
        self._action_groups = {}
        self._is_initialized = False
        logger.debug("Action manager initialized")

    async def initialize(self) -> None:
        """Initialize action manager."""
        try:
            if self._is_initialized:
                return

            # Load action definitions from process config
            process_config = await self._config_manager.get_config("process")
            if not process_config or "process" not in process_config:
                raise ConfigurationError("Missing process configuration")

            self._atomic_actions = process_config["process"].get("atomic_actions", {})
            self._action_groups = process_config["process"].get("action_groups", {})

            # Subscribe to message topics
            await self._message_broker.subscribe("action/request", self._handle_action_request)
            await self._message_broker.subscribe("action/group/request", self._handle_group_request)

            self._is_initialized = True
            logger.info("Action manager initialization complete")

        except Exception as e:
            error_msg = f"Failed to initialize action manager: {str(e)}"
            logger.error(error_msg)
            await self._message_broker.publish("error", {
                "source": "action_manager",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            raise OperationError("action_manager", error_msg)

    async def _handle_action_request(self, data: Dict[str, Any]) -> None:
        """Handle action request."""
        request_id = data.get("request_id")
        request_type = data.get("request_type")

        try:
            # Handle list request
            if request_type == "list":
                # Get list of available actions
                actions = list(self._atomic_actions.keys()) + list(self._action_groups.keys())
                actions.sort()

                # Send response
                await self._message_broker.publish(
                    "action/response",
                    {
                        "request_id": request_id,
                        "request_type": "list",
                        "success": True,
                        "actions": actions,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            # Handle execute request
            action = data.get("action")
            parameters = data.get("parameters", {})

            if not action:
                raise ValidationError("Missing action field")

            # Update state to running
            await self._message_broker.publish(
                "action/state",
                {
                    "request_id": request_id,
                    "action": action,
                    "state": "RUNNING",
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Execute action
            await self._execute_atomic_action(action, parameters)

            # Update state to completed
            await self._message_broker.publish(
                "action/state",
                {
                    "request_id": request_id,
                    "action": action,
                    "state": "COMPLETED",
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Send success response
            await self._message_broker.publish(
                "action/response",
                {
                    "request_id": request_id,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = f"Failed to execute action request: {str(e)}"
            logger.error(error_msg)

            # Update state to error if this was an execute request
            if request_type != "list":
                await self._message_broker.publish(
                    "action/state",
                    {
                        "request_id": request_id,
                        "action": data.get("action"),
                        "state": "ERROR",
                        "error": str(e),
                        "parameters": data.get("parameters", {}),
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Send error response
            await self._message_broker.publish(
                "action/response",
                {
                    "request_id": request_id,
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Publish to error topic
            await self._message_broker.publish(
                "error",
                {
                    "source": "action_manager",
                    "error": error_msg,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

            raise OperationError("action_manager", error_msg)

    async def _handle_group_request(self, data: Dict[str, Any]) -> None:
        """Handle action group request."""
        request_id = data.get("request_id")
        group = data.get("group")
        parameters = data.get("parameters", {})

        try:
            if not group:
                raise ValidationError("Missing group field")

            # Update state to running
            await self._message_broker.publish(
                "action/group/state",
                {
                    "request_id": request_id,
                    "group": group,
                    "state": "RUNNING",
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Execute group
            await self._execute_action_group(group, parameters)

            # Update state to completed
            await self._message_broker.publish(
                "action/group/state",
                {
                    "request_id": request_id,
                    "group": group,
                    "state": "COMPLETED",
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Send success response
            await self._message_broker.publish(
                "action/group/response",
                {
                    "request_id": request_id,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = f"Failed to execute action group {group}: {str(e)}"
            logger.error(error_msg)

            # Update state to error
            await self._message_broker.publish(
                "action/group/state",
                {
                    "request_id": request_id,
                    "group": group,
                    "state": "ERROR",
                    "error": str(e),
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Send error response
            await self._message_broker.publish(
                "action/group/response",
                {
                    "request_id": request_id,
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Publish to error topic
            await self._message_broker.publish(
                "error",
                {
                    "source": "action_manager",
                    "error": error_msg,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

            raise OperationError("action_manager", error_msg)

    async def _execute_atomic_action(self, action: str, parameters: Dict[str, Any]) -> None:
        """Execute an atomic action."""
        # Get action definition
        action_def = self._atomic_actions.get(action)
        if not action_def:
            raise ValidationError(f"Unknown action: {action}")

        # Execute action messages
        for msg in action_def.get("messages", []):
            await self._message_broker.publish(
                msg["topic"],
                {
                    "tags": msg["data"],
                    "parameters": parameters
                }
            )

    async def _execute_action_group(self, group: str, parameters: Dict[str, Any]) -> None:
        """Execute an action group."""
        # Get group definition
        group_def = self._action_groups.get(group)
        if not group_def:
            raise ValidationError(f"Unknown action group: {group}")

        # Execute each step
        total_steps = len(group_def.get("steps", []))
        for i, step in enumerate(group_def.get("steps", []), 1):
            # Update progress
            await self._message_broker.publish(
                "action/group/state",
                {
                    "group": group,
                    "state": "RUNNING",
                    "step": i,
                    "total_steps": total_steps,
                    "progress": (i / total_steps) * 100,
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )

            if "action" in step:
                await self._execute_atomic_action(
                    step["action"],
                    {**parameters, **step.get("parameters", {})}
                )

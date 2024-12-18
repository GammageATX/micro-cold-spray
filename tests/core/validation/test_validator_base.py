"""Tests for base validator."""

import re
import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any, List
from datetime import datetime

from micro_cold_spray.api.validation.validators.base import BaseValidator
from micro_cold_spray.api.validation.exceptions import TagError
from micro_cold_spray.api.messaging import MessagingService


class TestValidator(BaseValidator):
    """Test validator implementation."""
    async def validate(self, data: Dict[str, Any]) -> Dict[str, bool | List[str]]:
        """Test validation implementation."""
        return {"valid": True, "errors": [], "warnings": []}


@pytest.fixture
def validation_rules() -> Dict[str, Any]:
    """Create test validation rules."""
    return {
        "test": {
            "required_fields": ["field1", "field2"],
            "numeric_field": {
                "min": 0,
                "max": 100
            },
            "enum_field": {
                "choices": ["option1", "option2", "option3"]
            },
            "pattern_field": {
                "pattern": r"^test-\d+$"
            }
        }
    }


@pytest.fixture
def mock_message_broker():
    """Create mock message broker."""
    broker = AsyncMock(spec=MessagingService)
    broker.request.return_value = {"value": 42.0}
    return broker


@pytest.fixture
def validator(validation_rules, mock_message_broker):
    """Create base validator instance."""
    return TestValidator(validation_rules, mock_message_broker)


class TestBaseValidator:
    """Test base validator functionality."""

    async def test_get_tag_value_success(self, validator, mock_message_broker):
        """Test successful tag value retrieval."""
        value = await validator._get_tag_value("test.tag")
        assert value == 42.0
        mock_message_broker.request.assert_called_once_with(
            "tag/request",
            {"tag": "test.tag"}
        )

    async def test_get_tag_value_no_broker(self, validation_rules):
        """Test tag value retrieval with no message broker."""
        validator = TestValidator(validation_rules)
        with pytest.raises(TagError) as exc_info:
            await validator._get_tag_value("test.tag")
        assert "Message broker not available" in str(exc_info.value)

    async def test_get_tag_value_error(self, validator, mock_message_broker):
        """Test tag value retrieval error."""
        mock_message_broker.request.side_effect = Exception("Test error")
        with pytest.raises(TagError) as exc_info:
            await validator._get_tag_value("test.tag")
        assert "Failed to get tag value" in str(exc_info.value)

    def test_check_required_fields_success(self, validator):
        """Test required fields check with all fields present."""
        data = {"field1": "value1", "field2": "value2"}
        errors = validator._check_required_fields(data, ["field1", "field2"])
        assert len(errors) == 0

    def test_check_required_fields_missing(self, validator):
        """Test required fields check with missing fields."""
        data = {"field1": "value1"}
        errors = validator._check_required_fields(data, ["field1", "field2"])
        assert len(errors) == 1
        assert "Missing required field: field2" in errors[0]

    def test_check_required_fields_null(self, validator):
        """Test required fields check with null values."""
        data = {"field1": "value1", "field2": None}
        errors = validator._check_required_fields(data, ["field1", "field2"])
        assert len(errors) == 1
        assert "Field cannot be null: field2" in errors[0]

    def test_check_required_fields_with_prefix(self, validator):
        """Test required fields check with prefix."""
        data = {"field1": "value1"}
        errors = validator._check_required_fields(
            data,
            ["field1", "field2"],
            "Test: "
        )
        assert len(errors) == 1
        assert errors[0].startswith("Test: ")

    def test_check_unknown_fields_success(self, validator):
        """Test unknown fields check with valid fields."""
        data = {"field1": "value1", "field2": "value2"}
        errors = validator._check_unknown_fields(
            data,
            ["field1", "field2", "field3"]
        )
        assert len(errors) == 0

    def test_check_unknown_fields_invalid(self, validator):
        """Test unknown fields check with invalid fields."""
        data = {"field1": "value1", "invalid": "value"}
        errors = validator._check_unknown_fields(data, ["field1", "field2"])
        assert len(errors) == 1
        assert "Unknown field: invalid" in errors[0]

    def test_check_unknown_fields_with_prefix(self, validator):
        """Test unknown fields check with prefix."""
        data = {"field1": "value1", "invalid": "value"}
        errors = validator._check_unknown_fields(
            data,
            ["field1", "field2"],
            "Test: "
        )
        assert len(errors) == 1
        assert errors[0].startswith("Test: ")

    def test_check_numeric_range_success(self, validator):
        """Test numeric range check with valid values."""
        error = validator._check_numeric_range(50, 0, 100)
        assert error is None

        error = validator._check_numeric_range("50", 0, 100)
        assert error is None

    def test_check_numeric_range_below_min(self, validator):
        """Test numeric range check with value below minimum."""
        error = validator._check_numeric_range(-1, 0, 100)
        assert error is not None
        assert "below minimum" in error

    def test_check_numeric_range_above_max(self, validator):
        """Test numeric range check with value above maximum."""
        error = validator._check_numeric_range(150, 0, 100)
        assert error is not None
        assert "above maximum" in error

    def test_check_numeric_range_invalid_value(self, validator):
        """Test numeric range check with non-numeric value."""
        error = validator._check_numeric_range("not a number", 0, 100)
        assert error is not None
        assert "must be numeric" in error

    def test_check_numeric_range_with_field_name(self, validator):
        """Test numeric range check with custom field name."""
        error = validator._check_numeric_range(
            150,
            0,
            100,
            field_name="Test Field"
        )
        assert error is not None
        assert error.startswith("Test Field")

    def test_check_enum_value_success(self, validator):
        """Test enum value check with valid value."""
        error = validator._check_enum_value(
            "option1",
            ["option1", "option2", "option3"]
        )
        assert error is None

    def test_check_enum_value_invalid(self, validator):
        """Test enum value check with invalid value."""
        error = validator._check_enum_value(
            "invalid",
            ["option1", "option2", "option3"]
        )
        assert error is not None
        assert "must be one of" in error

    def test_check_enum_value_with_field_name(self, validator):
        """Test enum value check with custom field name."""
        error = validator._check_enum_value(
            "invalid",
            ["option1", "option2", "option3"],
            field_name="Test Field"
        )
        assert error is not None
        assert error.startswith("Test Field")

    def test_check_pattern_success(self, validator):
        """Test pattern check with valid value."""
        error = validator._check_pattern("test-123", r"^test-\d+$")
        assert error is None

        error = validator._check_pattern(
            "test-123",
            re.compile(r"^test-\d+$")
        )
        assert error is None

    def test_check_pattern_no_match(self, validator):
        """Test pattern check with non-matching value."""
        error = validator._check_pattern("invalid", r"^test-\d+$")
        assert error is not None
        assert "does not match pattern" in error

    def test_check_pattern_invalid_value(self, validator):
        """Test pattern check with non-string value."""
        error = validator._check_pattern(123, r"^test-\d+$")
        assert error is not None
        assert "must be string" in error

    def test_check_pattern_invalid_pattern(self, validator):
        """Test pattern check with invalid pattern."""
        error = validator._check_pattern("test", "[invalid")
        assert error is not None
        assert "Invalid pattern check" in error

    def test_check_pattern_with_field_name(self, validator):
        """Test pattern check with custom field name."""
        error = validator._check_pattern(
            "invalid",
            r"^test-\d+$",
            field_name="Test Field"
        )
        assert error is not None
        assert error.startswith("Test Field")

    def test_check_timestamp_success(self, validator):
        """Test timestamp check with valid values."""
        error = validator._check_timestamp("2024-01-01T12:00:00")
        assert error is None

        error = validator._check_timestamp(datetime.now())
        assert error is None

    def test_check_timestamp_invalid_format(self, validator):
        """Test timestamp check with invalid format."""
        error = validator._check_timestamp("invalid date")
        assert error is not None
        assert "must be valid ISO format" in error

    def test_check_timestamp_invalid_type(self, validator):
        """Test timestamp check with invalid type."""
        error = validator._check_timestamp(123)
        assert error is not None
        assert "must be ISO format string or datetime" in error

    def test_check_timestamp_with_field_name(self, validator):
        """Test timestamp check with custom field name."""
        error = validator._check_timestamp(
            "invalid date",
            field_name="Test Timestamp"
        )
        assert error is not None
        assert error.startswith("Test Timestamp")

    def test_format_error_basic(self, validator):
        """Test basic error formatting."""
        error = validator._format_error("Test error")
        assert error == "Test error"

    def test_format_error_with_field(self, validator):
        """Test error formatting with field name."""
        error = validator._format_error("Test error", "test_field")
        assert error == "test_field: Test error"

    def test_format_error_with_value(self, validator):
        """Test error formatting with value."""
        error = validator._format_error("Test error", value=42)
        assert error == "Test error (got: 42)"

    def test_format_error_complete(self, validator):
        """Test error formatting with all components."""
        error = validator._format_error("Test error", "test_field", 42)
        assert error == "test_field: Test error (got: 42)"

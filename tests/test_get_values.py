"""Tests for get_values functionality."""

import json
import pytest
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from google_sheets import GoogleSheetsMCP, mcp


class TestGetValues:
    """Test suite for get_values MCP tool."""

    @contextmanager
    def _setup_mcp_instance(self, mock_instance):
        """Context manager to temporarily set mcp._instance."""
        original_instance = getattr(mcp, '_instance', None)
        mcp._instance = mock_instance
        try:
            yield
        finally:
            if original_instance is not None:
                mcp._instance = original_instance
            else:
                if hasattr(mcp, '_instance'):
                    delattr(mcp, '_instance')

    @pytest.fixture
    def mock_instance(self):
        """Create a mock GoogleSheetsMCP instance with proper service mocking."""
        with patch('google_sheets.os.path.exists', return_value=False):
            instance = GoogleSheetsMCP(service_account_path="test_credentials.json")
            instance.sheets_service = Mock()
            instance.drive_service = Mock()
            return instance

    @pytest.mark.asyncio
    async def test_get_values_single_range(self, mock_instance):
        """Test getting values from a single range."""
        # Mock API response for single range
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {
                    "range": "Sheet1!A1:B2",
                    "values": [
                        ["Name", "Age"],
                        ["Alice", "30"]
                    ]
                }
            ]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Use context manager to set up mcp instance
        with self._setup_mcp_instance(mock_instance):
            result = await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges="Sheet1!A1:B2"
            )

            # Verify result
            assert isinstance(result, str)
            data = json.loads(result)
            assert data["spreadsheetId"] == "test123"
            assert len(data["valueRanges"]) == 1
            assert data["valueRanges"][0]["range"] == "Sheet1!A1:B2"
            assert data["valueRanges"][0]["values"] == [["Name", "Age"], ["Alice", "30"]]

    @pytest.mark.asyncio
    async def test_get_values_multiple_ranges(self, mock_instance):
        """Test getting values from multiple ranges."""
        # Mock API response for multiple ranges
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {
                    "range": "Sheet1!A1:B2",
                    "values": [
                        ["Name", "Age"],
                        ["Alice", "30"]
                    ]
                },
                {
                    "range": "Sheet2!C1:D3",
                    "values": [
                        ["Product", "Price"],
                        ["Apple", "1.99"],
                        ["Banana", "0.99"]
                    ]
                },
                {
                    "range": "Sheet1!E5:F6",
                    "values": [
                        ["Total", "100"],
                        ["Tax", "10"]
                    ]
                }
            ]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            result = await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges=["Sheet1!A1:B2", "Sheet2!C1:D3", "Sheet1!E5:F6"]
            )

        # Verify result
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["spreadsheetId"] == "test123"
        assert len(data["valueRanges"]) == 3
        
        # Check first range
        assert data["valueRanges"][0]["range"] == "Sheet1!A1:B2"
        assert data["valueRanges"][0]["values"] == [["Name", "Age"], ["Alice", "30"]]
        
        # Check second range
        assert data["valueRanges"][1]["range"] == "Sheet2!C1:D3"
        assert len(data["valueRanges"][1]["values"]) == 3
        
        # Check third range
        assert data["valueRanges"][2]["range"] == "Sheet1!E5:F6"
        assert data["valueRanges"][2]["values"][0] == ["Total", "100"]

        # Verify API call
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.assert_called_once_with(
            spreadsheetId="test123",
            ranges=["Sheet1!A1:B2", "Sheet2!C1:D3", "Sheet1!E5:F6"],
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING"
        )

    @pytest.mark.asyncio
    async def test_get_values_with_render_options(self, mock_instance):
        """Test getting values with custom render options."""
        # Mock API response
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {
                    "range": "Sheet1!A1:B2",
                    "values": [
                        ["=SUM(1,2)", "42"],
                        ["=A1*2", "84"]
                    ]
                }
            ]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            result = await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges="Sheet1!A1:B2",
                value_render_option="FORMULA",
                date_time_render_option="SERIAL_NUMBER"
            )

        # Verify API call with custom options
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.assert_called_once_with(
            spreadsheetId="test123",
            ranges=["Sheet1!A1:B2"],
            valueRenderOption="FORMULA",
            dateTimeRenderOption="SERIAL_NUMBER"
        )

    @pytest.mark.asyncio
    async def test_get_values_empty_range(self, mock_instance):
        """Test getting values from an empty range."""
        # Mock API response for empty range
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {
                    "range": "Sheet1!Z100:AA101"
                    # No "values" key when range is empty
                }
            ]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            result = await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges="Sheet1!Z100:AA101"
            )

        # Verify result handles empty range
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["spreadsheetId"] == "test123"
        assert len(data["valueRanges"]) == 1
        assert data["valueRanges"][0]["range"] == "Sheet1!Z100:AA101"
        assert "values" not in data["valueRanges"][0]

    @pytest.mark.asyncio
    async def test_get_values_mixed_empty_and_populated(self, mock_instance):
        """Test getting values with mix of empty and populated ranges."""
        # Mock API response
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {
                    "range": "Sheet1!A1:B2",
                    "values": [["Data", "123"]]
                },
                {
                    "range": "Sheet1!Z100:AA101"
                    # Empty range
                },
                {
                    "range": "Sheet2!A1:A3",
                    "values": [["One"], ["Two"], ["Three"]]
                }
            ]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            result = await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges=["Sheet1!A1:B2", "Sheet1!Z100:AA101", "Sheet2!A1:A3"]
            )

        # Verify mixed results
        data = json.loads(result)
        assert len(data["valueRanges"]) == 3
        assert "values" in data["valueRanges"][0]
        assert "values" not in data["valueRanges"][1]
        assert len(data["valueRanges"][2]["values"]) == 3

    @pytest.mark.asyncio
    async def test_get_values_invalid_file_id(self, mock_instance):
        """Test error handling for invalid file ID."""
        # Mock API error
        mock_batch_get = Mock()
        mock_batch_get.execute.side_effect = Exception("File not found")
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            with pytest.raises(Exception) as exc_info:
                await GoogleSheetsMCP.get_values(
                    file_id="invalid123",
                    ranges="Sheet1!A1:B2"
                )
            
            assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_values_invalid_range_format(self, mock_instance):
        """Test error handling for invalid range format."""
        # Mock API error for invalid range
        mock_batch_get = Mock()
        mock_batch_get.execute.side_effect = Exception("Invalid range")
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            with pytest.raises(Exception) as exc_info:
                await GoogleSheetsMCP.get_values(
                    file_id="test123",
                    ranges="InvalidRange"
                )
            
            assert "Invalid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_values_normalizes_single_range_to_list(self, mock_instance):
        """Test that single range string is normalized to list for API call."""
        # Mock successful response
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [{"range": "A1:B2", "values": [["test"]]}]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            # Pass ranges as string
            await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges="A1:B2"
            )

        # Verify it was converted to list for API
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.assert_called_once()
        call_args = mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.call_args[1]
        assert isinstance(call_args["ranges"], list)
        assert call_args["ranges"] == ["A1:B2"]

    @pytest.mark.asyncio
    async def test_get_values_preserves_data_types(self, mock_instance):
        """Test that various data types are preserved correctly."""
        # Mock API response with various data types
        mock_batch_get = Mock()
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {
                    "range": "Sheet1!A1:D3",
                    "values": [
                        ["String", "123", "45.67", "TRUE"],
                        ["Test", "456", "89.01", "FALSE"],
                        ["", "0", "-12.34", ""]
                    ]
                }
            ]
        }
        mock_instance.sheets_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get

        # Set up mcp instance using context manager
        with self._setup_mcp_instance(mock_instance):
            result = await GoogleSheetsMCP.get_values(
                file_id="test123",
                ranges="Sheet1!A1:D3"
            )

        # Verify data types are preserved as strings
        data = json.loads(result)
        values = data["valueRanges"][0]["values"]
        assert values[0] == ["String", "123", "45.67", "TRUE"]
        assert values[1] == ["Test", "456", "89.01", "FALSE"]
        assert values[2] == ["", "0", "-12.34", ""]
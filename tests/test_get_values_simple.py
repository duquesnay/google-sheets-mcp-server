"""Simplified tests for get_values functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from google_sheets import GoogleSheetsMCP, mcp


class TestGetValuesSimple:
    """Simplified test suite focusing on the core functionality."""

    @pytest.fixture(autouse=True)
    def setup_mcp(self):
        """Automatically set up MCP instance for all tests."""
        # Create a mock instance
        mock_instance = MagicMock(spec=GoogleSheetsMCP)
        
        # Store original and set mock
        original = getattr(mcp, '_instance', None)
        mcp._instance = mock_instance
        
        yield mock_instance
        
        # Restore original
        if original is not None:
            mcp._instance = original
        else:
            if hasattr(mcp, '_instance'):
                delattr(mcp, '_instance')

    @pytest.mark.asyncio
    async def test_get_values_calls_impl_single_range(self, setup_mcp):
        """Test that get_values properly delegates to _get_values_impl for single range."""
        # Mock the implementation method
        expected_result = json.dumps({
            "spreadsheetId": "test123",
            "valueRanges": [{"range": "A1:B2", "values": [["1", "2"]]}]
        })
        setup_mcp._get_values_impl = AsyncMock(return_value=expected_result)
        
        # Call the MCP handler
        result = await GoogleSheetsMCP.get_values(
            file_id="test123",
            ranges="A1:B2"
        )
        
        # Verify result
        assert result == expected_result
        
        # Verify the implementation was called correctly
        setup_mcp._get_values_impl.assert_called_once_with(
            file_id="test123",
            ranges="A1:B2",
            value_render_option="FORMATTED_VALUE",
            date_time_render_option="FORMATTED_STRING"
        )

    @pytest.mark.asyncio
    async def test_get_values_calls_impl_multiple_ranges(self, setup_mcp):
        """Test that get_values properly delegates to _get_values_impl for multiple ranges."""
        # Mock the implementation method
        expected_result = json.dumps({
            "spreadsheetId": "test123",
            "valueRanges": [
                {"range": "A1:B2", "values": [["1", "2"]]},
                {"range": "C3:D4", "values": [["3", "4"]]}
            ]
        })
        setup_mcp._get_values_impl = AsyncMock(return_value=expected_result)
        
        # Call the MCP handler
        result = await GoogleSheetsMCP.get_values(
            file_id="test123",
            ranges=["A1:B2", "C3:D4"]
        )
        
        # Verify result
        assert result == expected_result
        
        # Verify the implementation was called correctly
        setup_mcp._get_values_impl.assert_called_once_with(
            file_id="test123",
            ranges=["A1:B2", "C3:D4"],
            value_render_option="FORMATTED_VALUE",
            date_time_render_option="FORMATTED_STRING"
        )

    @pytest.mark.asyncio
    async def test_get_values_with_custom_options(self, setup_mcp):
        """Test that get_values passes custom render options."""
        # Mock the implementation method
        expected_result = json.dumps({
            "spreadsheetId": "test123",
            "valueRanges": [{"range": "A1:B2", "values": [["=SUM(1,2)", "=A1*2"]]}]
        })
        setup_mcp._get_values_impl = AsyncMock(return_value=expected_result)
        
        # Call with custom options
        result = await GoogleSheetsMCP.get_values(
            file_id="test123",
            ranges="A1:B2",
            value_render_option="FORMULA",
            date_time_render_option="SERIAL_NUMBER"
        )
        
        # Verify the implementation was called with custom options
        setup_mcp._get_values_impl.assert_called_once_with(
            file_id="test123",
            ranges="A1:B2",
            value_render_option="FORMULA",
            date_time_render_option="SERIAL_NUMBER"
        )

    @pytest.mark.asyncio
    async def test_get_values_impl_single_range(self, setup_mcp):
        """Test the _get_values_impl method with single range."""
        # Create a real instance for testing the implementation
        instance = GoogleSheetsMCP()
        
        # Mock the sheets service
        mock_service = MagicMock()
        mock_values = MagicMock()
        mock_batch_get = MagicMock()
        
        instance.sheets_service = mock_service
        mock_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get
        
        # Mock the execute response
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {"range": "Sheet1!A1:B2", "values": [["Name", "Age"], ["Alice", "30"]]}
            ]
        }
        
        # Call the implementation
        result = await instance._get_values_impl(
            file_id="test123",
            ranges="Sheet1!A1:B2"
        )
        
        # Verify result
        data = json.loads(result)
        assert data["spreadsheetId"] == "test123"
        assert len(data["valueRanges"]) == 1
        assert data["valueRanges"][0]["values"] == [["Name", "Age"], ["Alice", "30"]]
        
        # Verify API was called correctly
        mock_service.spreadsheets().values().batchGet.assert_called_once_with(
            spreadsheetId="test123",
            ranges=["Sheet1!A1:B2"],  # Should be converted to list
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING"
        )

    @pytest.mark.asyncio
    async def test_get_values_impl_multiple_ranges(self, setup_mcp):
        """Test the _get_values_impl method with multiple ranges."""
        # Create a real instance
        instance = GoogleSheetsMCP()
        
        # Mock the sheets service
        mock_service = MagicMock()
        mock_values = MagicMock()
        mock_batch_get = MagicMock()
        
        instance.sheets_service = mock_service
        mock_service.spreadsheets.return_value.values.return_value.batchGet.return_value = mock_batch_get
        
        # Mock the execute response
        mock_batch_get.execute.return_value = {
            "spreadsheetId": "test123",
            "valueRanges": [
                {"range": "Sheet1!A1:B2", "values": [["1", "2"]]},
                {"range": "Sheet2!C1:D2", "values": [["3", "4"]]},
                {"range": "Sheet1!E1:F2", "values": [["5", "6"]]}
            ]
        }
        
        # Call the implementation
        result = await instance._get_values_impl(
            file_id="test123",
            ranges=["Sheet1!A1:B2", "Sheet2!C1:D2", "Sheet1!E1:F2"]
        )
        
        # Verify result
        data = json.loads(result)
        assert data["spreadsheetId"] == "test123"
        assert len(data["valueRanges"]) == 3
        
        # Verify API was called correctly
        mock_service.spreadsheets().values().batchGet.assert_called_once_with(
            spreadsheetId="test123",
            ranges=["Sheet1!A1:B2", "Sheet2!C1:D2", "Sheet1!E1:F2"],
            valueRenderOption="FORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING"
        )
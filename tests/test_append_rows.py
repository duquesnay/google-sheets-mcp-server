"""Tests for append_rows functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_sheets import GoogleSheetsMCP, mcp


class TestAppendRows:
    """Unit tests for append_rows functionality."""

    @pytest.fixture
    def mock_sheets_service(self):
        """Create a mock Google Sheets service."""
        service = MagicMock()
        return service

    @pytest.fixture
    def google_sheets_instance(self, mock_sheets_service):
        """Create GoogleSheetsMCP instance with mocked service."""
        instance = GoogleSheetsMCP()
        instance.sheets_service = mock_sheets_service
        mcp._instance = instance
        return instance

    @pytest.mark.asyncio
    async def test_append_single_row(self, google_sheets_instance, mock_sheets_service):
        """Test appending a single row of data."""
        # Setup
        file_id = "test123"
        range_name = "Sheet1"
        values = [["Cell1", "Cell2", "Cell3"]]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!A2:C2",
                "updatedRows": 1,
                "updatedColumns": 3,
                "updatedCells": 3
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["spreadsheetId"] == file_id
        assert result_data["updatedRows"] == 1
        assert result_data["updatedCells"] == 3
        assert "Sheet1!A2:C2" in result_data["updatedRange"]
        
        # Verify API call
        mock_sheets_service.spreadsheets().values().append.assert_called_once()
        call_kwargs = mock_sheets_service.spreadsheets().values().append.call_args.kwargs
        assert call_kwargs["spreadsheetId"] == file_id
        assert call_kwargs["range"] == range_name
        # Values should be converted to strings in the implementation
        assert len(call_kwargs["body"]["values"]) == len(values)
        assert len(call_kwargs["body"]["values"][0]) == len(values[0])

    @pytest.mark.asyncio
    async def test_append_multiple_rows(self, google_sheets_instance, mock_sheets_service):
        """Test appending multiple rows of data."""
        # Setup
        file_id = "test456"
        range_name = "Sheet1"
        values = [
            ["Row1Col1", "Row1Col2", "Row1Col3"],
            ["Row2Col1", "Row2Col2", "Row2Col3"],
            ["Row3Col1", "Row3Col2", "Row3Col3"]
        ]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!A5:C7",
                "updatedRows": 3,
                "updatedColumns": 3,
                "updatedCells": 9
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 3
        assert result_data["updatedCells"] == 9
        
    @pytest.mark.asyncio
    async def test_append_with_different_data_types(self, google_sheets_instance, mock_sheets_service):
        """Test appending rows with mixed data types."""
        # Setup
        file_id = "test789"
        range_name = "Sheet1"
        values = [
            ["String", 123, 45.67, True, None],
            ["", 0, -10.5, False, "=SUM(A1:A10)"]
        ]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!A10:E11",
                "updatedRows": 2,
                "updatedColumns": 5,
                "updatedCells": 10
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 2
        assert result_data["updatedColumns"] == 5
        
        # Verify the values were passed correctly
        call_kwargs = mock_sheets_service.spreadsheets().values().append.call_args.kwargs
        # Values are converted to strings in implementation
        assert len(call_kwargs["body"]["values"]) == len(values)
        assert len(call_kwargs["body"]["values"][0]) == len(values[0])

    @pytest.mark.asyncio
    async def test_append_empty_rows(self, google_sheets_instance, mock_sheets_service):
        """Test appending empty rows (spacing)."""
        # Setup
        file_id = "test_empty"
        range_name = "Sheet1"
        values = [
            ["Data1", "Data2"],
            ["", ""],  # Empty row
            ["Data3", "Data4"]
        ]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!A15:B17",
                "updatedRows": 3,
                "updatedColumns": 2,
                "updatedCells": 6
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 3

    @pytest.mark.asyncio
    async def test_append_with_value_input_option(self, google_sheets_instance, mock_sheets_service):
        """Test appending with different value input options."""
        # Setup
        file_id = "test_input"
        range_name = "Sheet1"
        values = [["=A1+B1", "100", "=SUM(A:A)"]]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!A20:C20",
                "updatedRows": 1,
                "updatedColumns": 3,
                "updatedCells": 3
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute with USER_ENTERED (formulas will be parsed)
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values,
            value_input_option="USER_ENTERED"
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 1
        
        # Verify the input option was passed
        call_kwargs = mock_sheets_service.spreadsheets().values().append.call_args.kwargs
        assert call_kwargs["valueInputOption"] == "USER_ENTERED"

    @pytest.mark.asyncio
    async def test_append_to_specific_range(self, google_sheets_instance, mock_sheets_service):
        """Test appending to a specific column range."""
        # Setup
        file_id = "test_range"
        range_name = "Sheet1!C:E"  # Append to columns C-E
        values = [["Col C", "Col D", "Col E"]]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!C25:E25",
                "updatedRows": 1,
                "updatedColumns": 3,
                "updatedCells": 3
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values
        )
        
        # Verify
        result_data = json.loads(result)
        assert "C25:E25" in result_data["updatedRange"]

    @pytest.mark.asyncio
    async def test_append_with_insert_data_option(self, google_sheets_instance, mock_sheets_service):
        """Test different insert data options."""
        # Setup
        file_id = "test_insert"
        range_name = "Sheet1"
        values = [["New Data"]]
        
        mock_response = {
            "spreadsheetId": file_id,
            "updates": {
                "spreadsheetId": file_id,
                "updatedRange": "Sheet1!A30",
                "updatedRows": 1,
                "updatedColumns": 1,
                "updatedCells": 1
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute with INSERT_ROWS option
        result = await GoogleSheetsMCP.append_rows(
            file_id=file_id,
            range=range_name,
            values=values,
            insert_data_option="INSERT_ROWS"
        )
        
        # Verify
        call_kwargs = mock_sheets_service.spreadsheets().values().append.call_args.kwargs
        assert call_kwargs["insertDataOption"] == "INSERT_ROWS"

    @pytest.mark.asyncio
    async def test_append_validation_errors(self, google_sheets_instance):
        """Test validation of input parameters."""
        # Test missing file_id
        with pytest.raises(TypeError):
            await GoogleSheetsMCP.append_rows(
                range="Sheet1",
                values=[["data"]]
            )
        
        # Test missing range
        with pytest.raises(TypeError):
            await GoogleSheetsMCP.append_rows(
                file_id="test123",
                values=[["data"]]
            )
        
        # Test missing values
        with pytest.raises(TypeError):
            await GoogleSheetsMCP.append_rows(
                file_id="test123",
                range="Sheet1"
            )
        
        # Test empty values
        with pytest.raises(ValueError, match="values cannot be empty"):
            await GoogleSheetsMCP.append_rows(
                file_id="test123",
                range="Sheet1",
                values=[]
            )
        
        # Test invalid value_input_option
        with pytest.raises(ValueError, match="Invalid value_input_option"):
            await GoogleSheetsMCP.append_rows(
                file_id="test123",
                range="Sheet1",
                values=[["data"]],
                value_input_option="INVALID"
            )

    @pytest.mark.asyncio
    async def test_append_api_error_handling(self, google_sheets_instance, mock_sheets_service):
        """Test handling of Google Sheets API errors."""
        # Setup
        mock_sheets_service.spreadsheets().values().append.return_value.execute.side_effect = Exception("API Error: Invalid range")
        
        # Execute and expect error
        with pytest.raises(Exception, match="API Error: Invalid range"):
            await GoogleSheetsMCP.append_rows(
                file_id="test123",
                range="InvalidSheet",
                values=[["data"]]
            )

    @pytest.mark.asyncio 
    async def test_mcp_handler_returns_json_string(self, google_sheets_instance, mock_sheets_service):
        """Test that MCP handler returns JSON string, not object."""
        # Setup
        mock_response = {
            "spreadsheetId": "test123",
            "updates": {
                "spreadsheetId": "test123",
                "updatedRange": "Sheet1!A1:A1",
                "updatedRows": 1,
                "updatedColumns": 1,
                "updatedCells": 1
            }
        }
        
        mock_sheets_service.spreadsheets().values().append.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.append_rows(
            file_id="test123",
            range="Sheet1",
            values=[["test"]]
        )
        
        # Verify result is a string
        assert isinstance(result, str)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["spreadsheetId"] == "test123"
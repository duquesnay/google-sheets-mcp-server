"""Tests for insert_rows functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_sheets import GoogleSheetsMCP, mcp


class TestInsertRows:
    """Unit tests for insert_rows functionality."""

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
    async def test_insert_single_row_empty(self, google_sheets_instance, mock_sheets_service):
        """Test inserting a single empty row."""
        # Setup
        file_id = "test123"
        sheet_id = 0
        start_index = 1  # Insert after row 1 (before current row 2)
        num_rows = 1
        
        mock_response = {
            "spreadsheetId": file_id,
            "replies": [
                {
                    "addDimensionGroup": {}
                }
            ]
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["spreadsheetId"] == file_id
        assert result_data["insertedRows"] == num_rows
        assert result_data["startIndex"] == start_index
        
        # Verify API call structure
        mock_sheets_service.spreadsheets().batchUpdate.assert_called_once()
        call_kwargs = mock_sheets_service.spreadsheets().batchUpdate.call_args.kwargs
        assert call_kwargs["spreadsheetId"] == file_id
        
        requests = call_kwargs["body"]["requests"]
        assert len(requests) == 1
        insert_request = requests[0]["insertDimension"]
        assert insert_request["range"]["sheetId"] == sheet_id
        assert insert_request["range"]["dimension"] == "ROWS"
        assert insert_request["range"]["startIndex"] == start_index
        assert insert_request["range"]["endIndex"] == start_index + num_rows

    @pytest.mark.asyncio
    async def test_insert_multiple_rows_empty(self, google_sheets_instance, mock_sheets_service):
        """Test inserting multiple empty rows."""
        # Setup
        file_id = "test456"
        sheet_id = 0
        start_index = 5
        num_rows = 3
        
        mock_response = {
            "spreadsheetId": file_id,
            "replies": [
                {
                    "addDimensionGroup": {}
                }
            ]
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["insertedRows"] == num_rows
        assert result_data["startIndex"] == start_index
        
        # Verify API call
        call_kwargs = mock_sheets_service.spreadsheets().batchUpdate.call_args.kwargs
        insert_request = call_kwargs["body"]["requests"][0]["insertDimension"]
        assert insert_request["range"]["endIndex"] == start_index + num_rows

    @pytest.mark.asyncio
    async def test_insert_rows_with_data(self, google_sheets_instance, mock_sheets_service):
        """Test inserting rows with data."""
        # Setup
        file_id = "test789"
        sheet_id = 0
        start_index = 2
        num_rows = 2
        values = [
            ["Row1Col1", "Row1Col2", "Row1Col3"],
            ["Row2Col1", "Row2Col2", "Row2Col3"]
        ]
        
        mock_batch_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_update_response = {
            "spreadsheetId": file_id,
            "updatedRange": "Sheet1!A3:C4",
            "updatedRows": 2,
            "updatedColumns": 3,
            "updatedCells": 6
        }
        
        # Mock both batch update for insertion and values update for data
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_batch_response
        mock_sheets_service.spreadsheets().values().update.return_value.execute.return_value = mock_update_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows,
            values=values
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["insertedRows"] == num_rows
        assert result_data["updatedCells"] == 6
        
        # Verify both API calls were made
        mock_sheets_service.spreadsheets().batchUpdate.assert_called_once()
        mock_sheets_service.spreadsheets().values().update.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_rows_with_sheet_name(self, google_sheets_instance, mock_sheets_service):
        """Test inserting rows using sheet name instead of ID."""
        # Setup
        file_id = "test_sheet_name"
        sheet_name = "MySheet"
        start_index = 0  # Insert at beginning
        num_rows = 1
        
        # Mock get spreadsheet response to return sheet properties
        mock_spreadsheet_response = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": 123456789,
                        "title": "MySheet"
                    }
                },
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1"
                    }
                }
            ]
        }
        
        mock_batch_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_sheets_service.spreadsheets().get.return_value.execute.return_value = mock_spreadsheet_response
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_batch_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_name=sheet_name,
            start_index=start_index,
            num_rows=num_rows
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["sheetId"] == 123456789
        
        # Verify sheet properties were fetched
        mock_sheets_service.spreadsheets().get.assert_called_once_with(
            spreadsheetId=file_id,
            fields="sheets.properties"
        )

    @pytest.mark.asyncio
    async def test_insert_rows_with_mixed_data_types(self, google_sheets_instance, mock_sheets_service):
        """Test inserting rows with mixed data types."""
        # Setup
        file_id = "test_mixed"
        sheet_id = 0
        start_index = 3
        num_rows = 1
        values = [["String", 123, 45.67, True, None, "=SUM(A1:A10)"]]
        
        mock_batch_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_update_response = {
            "spreadsheetId": file_id,
            "updatedRange": "Sheet1!A4:F4",
            "updatedRows": 1,
            "updatedColumns": 6,
            "updatedCells": 6
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_batch_response
        mock_sheets_service.spreadsheets().values().update.return_value.execute.return_value = mock_update_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows,
            values=values,
            value_input_option="USER_ENTERED"
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["updatedCells"] == 6
        
        # Verify values update was called with correct parameters
        call_kwargs = mock_sheets_service.spreadsheets().values().update.call_args.kwargs
        assert call_kwargs["valueInputOption"] == "USER_ENTERED"

    @pytest.mark.asyncio
    async def test_insert_rows_at_beginning(self, google_sheets_instance, mock_sheets_service):
        """Test inserting rows at the very beginning (index 0)."""
        # Setup
        file_id = "test_beginning"
        sheet_id = 0
        start_index = 0
        num_rows = 2
        
        mock_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["startIndex"] == 0
        
        # Verify API call
        call_kwargs = mock_sheets_service.spreadsheets().batchUpdate.call_args.kwargs
        insert_request = call_kwargs["body"]["requests"][0]["insertDimension"]
        assert insert_request["range"]["startIndex"] == 0
        assert insert_request["range"]["endIndex"] == 2

    @pytest.mark.asyncio
    async def test_insert_rows_inherit_properties(self, google_sheets_instance, mock_sheets_service):
        """Test inserting rows with inherit_from_before option."""
        # Setup
        file_id = "test_inherit"
        sheet_id = 0
        start_index = 5
        num_rows = 1
        
        mock_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows,
            inherit_from_before=True
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["insertedRows"] == num_rows
        
        # Verify API call includes inheritFromBefore
        call_kwargs = mock_sheets_service.spreadsheets().batchUpdate.call_args.kwargs
        insert_request = call_kwargs["body"]["requests"][0]["insertDimension"]
        assert insert_request.get("inheritFromBefore", False) == True

    @pytest.mark.asyncio
    async def test_insert_rows_validation_errors(self, google_sheets_instance):
        """Test validation of input parameters."""
        # Test missing file_id
        with pytest.raises(TypeError):
            await GoogleSheetsMCP.insert_rows(
                sheet_id=0,
                start_index=1,
                num_rows=1
            )
        
        # Test missing sheet identifier (neither sheet_id nor sheet_name)
        with pytest.raises(ValueError, match="Either sheet_id or sheet_name must be provided"):
            await GoogleSheetsMCP.insert_rows(
                file_id="test123",
                start_index=1,
                num_rows=1
            )
        
        # Test negative start_index
        with pytest.raises(ValueError, match="start_index must be non-negative"):
            await GoogleSheetsMCP.insert_rows(
                file_id="test123",
                sheet_id=0,
                start_index=-1,
                num_rows=1
            )
        
        # Test zero or negative num_rows
        with pytest.raises(ValueError, match="num_rows must be positive"):
            await GoogleSheetsMCP.insert_rows(
                file_id="test123",
                sheet_id=0,
                start_index=1,
                num_rows=0
            )
        
        # Test mismatch between num_rows and values length
        with pytest.raises(ValueError, match="values list length .* does not match num_rows"):
            await GoogleSheetsMCP.insert_rows(
                file_id="test123",
                sheet_id=0,
                start_index=1,
                num_rows=2,
                values=[["only one row"]]
            )

    @pytest.mark.asyncio
    async def test_insert_rows_sheet_not_found(self, google_sheets_instance, mock_sheets_service):
        """Test handling when sheet name is not found."""
        # Setup
        file_id = "test_not_found"
        sheet_name = "NonExistentSheet"
        
        mock_spreadsheet_response = {
            "sheets": [
                {
                    "properties": {
                        "sheetId": 0,
                        "title": "Sheet1"
                    }
                }
            ]
        }
        
        mock_sheets_service.spreadsheets().get.return_value.execute.return_value = mock_spreadsheet_response
        
        # Execute and expect error
        with pytest.raises(ValueError, match="Sheet 'NonExistentSheet' not found"):
            await GoogleSheetsMCP.insert_rows(
                file_id=file_id,
                sheet_name=sheet_name,
                start_index=1,
                num_rows=1
            )

    @pytest.mark.asyncio
    async def test_insert_rows_api_error_handling(self, google_sheets_instance, mock_sheets_service):
        """Test handling of Google Sheets API errors."""
        # Setup
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.side_effect = Exception("API Error: Invalid request")
        
        # Execute and expect error
        with pytest.raises(Exception, match="API Error: Invalid request"):
            await GoogleSheetsMCP.insert_rows(
                file_id="test123",
                sheet_id=0,
                start_index=1,
                num_rows=1
            )

    @pytest.mark.asyncio 
    async def test_mcp_handler_returns_json_string(self, google_sheets_instance, mock_sheets_service):
        """Test that MCP handler returns JSON string, not object."""
        # Setup
        mock_response = {
            "spreadsheetId": "test123",
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id="test123",
            sheet_id=0,
            start_index=1,
            num_rows=1
        )
        
        # Verify result is a string
        assert isinstance(result, str)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["spreadsheetId"] == "test123"

    @pytest.mark.asyncio
    async def test_insert_rows_large_batch(self, google_sheets_instance, mock_sheets_service):
        """Test inserting a large number of rows."""
        # Setup
        file_id = "test_large"
        sheet_id = 0
        start_index = 10
        num_rows = 100
        
        mock_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["insertedRows"] == 100
        
        # Verify API call
        call_kwargs = mock_sheets_service.spreadsheets().batchUpdate.call_args.kwargs
        insert_request = call_kwargs["body"]["requests"][0]["insertDimension"]
        assert insert_request["range"]["endIndex"] == start_index + num_rows

    @pytest.mark.asyncio
    async def test_insert_rows_with_range_specification(self, google_sheets_instance, mock_sheets_service):
        """Test inserting rows with values and specific range."""
        # Setup
        file_id = "test_range"
        sheet_id = 0
        start_index = 3
        num_rows = 2
        values = [
            ["A1", "B1", "C1"],
            ["A2", "B2", "C2"]
        ]
        range_name = "MySheet!A4:C5"  # Specific range for the data
        
        mock_batch_response = {
            "spreadsheetId": file_id,
            "replies": [{"addDimensionGroup": {}}]
        }
        
        mock_update_response = {
            "spreadsheetId": file_id,
            "updatedRange": range_name,
            "updatedRows": 2,
            "updatedColumns": 3,
            "updatedCells": 6
        }
        
        mock_sheets_service.spreadsheets().batchUpdate.return_value.execute.return_value = mock_batch_response
        mock_sheets_service.spreadsheets().values().update.return_value.execute.return_value = mock_update_response
        
        # Execute
        result = await GoogleSheetsMCP.insert_rows(
            file_id=file_id,
            sheet_id=sheet_id,
            start_index=start_index,
            num_rows=num_rows,
            values=values,
            range=range_name
        )
        
        # Verify
        result_data = json.loads(result)
        assert result_data["updatedRange"] == range_name
        
        # Verify values update was called with the specified range
        call_kwargs = mock_sheets_service.spreadsheets().values().update.call_args.kwargs
        assert call_kwargs["range"] == range_name
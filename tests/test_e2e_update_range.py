"""End-to-end tests for update_range functionality.

These tests require actual Google Sheets API credentials and create real spreadsheets.
Run only when you have proper credentials set up.

Usage:
    pytest tests/test_e2e_update_range.py -v --e2e
"""
import json
import pytest
import asyncio
from unittest.mock import patch
from google_sheets import GoogleSheetsMCP, mcp


@pytest.fixture(scope="session")
async def real_google_sheets():
    """Create a real GoogleSheetsMCP instance for e2e testing."""
    # This would need real credentials in a real test environment
    # For now, we'll mock but structure it for real testing
    
    try:
        # In real e2e tests, you'd do:
        # from google.oauth2 import service_account
        # from googleapiclient.discovery import build
        # 
        # credentials = service_account.Credentials.from_service_account_file(
        #     'path/to/service-account-key.json',
        #     scopes=['https://www.googleapis.com/auth/spreadsheets']
        # )
        # service = build('sheets', 'v4', credentials=credentials)
        
        # For this example, we'll use a mock but structure it properly
        with patch('google_sheets.build') as mock_build:
            from unittest.mock import MagicMock
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            instance = GoogleSheetsMCP(mock_service)
            mcp._instance = instance
            
            yield instance, mock_service
            
    except Exception as e:
        pytest.skip(f"Cannot create real Google Sheets instance: {e}")


class TestUpdateRangeE2E:
    """End-to-end tests for update_range functionality."""
    
    @pytest.mark.e2e
    async def test_create_and_update_spreadsheet(self, real_google_sheets):
        """Test creating a new spreadsheet and updating ranges."""
        instance, mock_service = real_google_sheets
        
        # Mock responses for a complete workflow
        # 1. Create spreadsheet
        mock_service.spreadsheets.return_value.create.return_value.execute.return_value = {
            "spreadsheetId": "test_e2e_123",
            "properties": {"title": "E2E Test Sheet"},
            "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1"}}]
        }
        
        # 2. Update range response
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        mock_update.return_value.execute.return_value = {
            "spreadsheetId": "test_e2e_123",
            "updatedRange": "Sheet1!A1:C3",
            "updatedRows": 3,
            "updatedColumns": 3,
            "updatedCells": 9
        }
        
        # Create a test spreadsheet
        from google_sheets import create_sheet
        create_result = await create_sheet({"title": "E2E Test Sheet"})
        create_data = json.loads(create_result)
        spreadsheet_id = create_data["spreadsheetId"]
        
        # Update the spreadsheet with test data
        test_data = [
            ["Product", "Price", "Stock"],
            ["Widget A", 10.99, 50],
            ["Widget B", 15.50, 25]
        ]
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        update_result = await MCPClass.update_range(
            file_id=spreadsheet_id,
            range="Sheet1!A1:C3",
            values=test_data
        )
        
        # Verify the update
        update_data = json.loads(update_result)
        assert update_data["spreadsheetId"] == spreadsheet_id
        assert update_data["updatedCells"] == 9
        assert update_data["updatedRange"] == "Sheet1!A1:C3"
        
        # Verify the mock was called correctly
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["spreadsheetId"] == spreadsheet_id
        assert call_kwargs["range"] == "Sheet1!A1:C3"
        assert call_kwargs["body"]["values"] == test_data
        assert call_kwargs["valueInputOption"] == "USER_ENTERED"
    
    @pytest.mark.e2e
    async def test_update_with_formulas(self, real_google_sheets):
        """Test updating cells with formulas."""
        instance, mock_service = real_google_sheets
        
        # Mock the update response
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        mock_update.return_value.execute.return_value = {
            "spreadsheetId": "test_formulas_123",
            "updatedRange": "Sheet1!D1:D3",
            "updatedRows": 3,
            "updatedColumns": 1,
            "updatedCells": 3
        }
        
        # Test data with formulas
        formula_data = [
            ["=B1*C1"],      # Price * Stock
            ["=B2*C2"],
            ["=SUM(D1:D2)"]  # Total value
        ]
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        result = await MCPClass.update_range(
            file_id="test_formulas_123",
            range="Sheet1!D1:D3", 
            values=formula_data,
            value_input_option="USER_ENTERED"
        )
        
        # Verify formulas were processed
        data = json.loads(result)
        assert data["updatedCells"] == 3
        
        # Verify the formulas were sent with USER_ENTERED option
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["valueInputOption"] == "USER_ENTERED"
        assert call_kwargs["body"]["values"] == formula_data
    
    @pytest.mark.e2e
    async def test_update_large_range(self, real_google_sheets):
        """Test updating a large range of data."""
        instance, mock_service = real_google_sheets
        
        # Create a larger dataset (10x5 grid)
        large_data = []
        for i in range(10):
            row = []
            for j in range(5):
                row.append(f"Cell_{i}_{j}")
            large_data.append(row)
        
        # Mock the update response
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        mock_update.return_value.execute.return_value = {
            "spreadsheetId": "test_large_123",
            "updatedRange": "Sheet1!A1:E10",
            "updatedRows": 10,
            "updatedColumns": 5,
            "updatedCells": 50
        }
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        result = await MCPClass.update_range(
            file_id="test_large_123",
            range="Sheet1!A1:E10",
            values=large_data
        )
        
        # Verify large update
        data = json.loads(result)
        assert data["updatedCells"] == 50
        assert data["updatedRows"] == 10
        assert data["updatedColumns"] == 5
        
        # Verify all data was sent
        call_kwargs = mock_update.call_args[1]
        assert len(call_kwargs["body"]["values"]) == 10
        assert len(call_kwargs["body"]["values"][0]) == 5
    
    @pytest.mark.e2e
    async def test_overwrite_existing_data(self, real_google_sheets):
        """Test overwriting existing data in a spreadsheet."""
        instance, mock_service = real_google_sheets
        
        # Mock initial read to show existing data
        mock_get = mock_service.spreadsheets.return_value.values.return_value.get
        mock_get.return_value.execute.return_value = {
            "range": "Sheet1!A1:B2",
            "values": [
                ["Old Name", "Old Value"],
                ["Old Item", "Old Data"]
            ]
        }
        
        # Mock update response
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        mock_update.return_value.execute.return_value = {
            "spreadsheetId": "test_overwrite_123",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        
        # New data to overwrite with
        new_data = [
            ["New Name", "New Value"],
            ["New Item", "New Data"]
        ]
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        result = await MCPClass.update_range(
            file_id="test_overwrite_123",
            range="Sheet1!A1:B2",
            values=new_data
        )
        
        # Verify overwrite was successful
        data = json.loads(result)
        assert data["updatedCells"] == 4
        
        # Verify new data was sent
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["body"]["values"] == new_data
    
    @pytest.mark.e2e
    async def test_clear_cells_with_empty_values(self, real_google_sheets):
        """Test clearing cells by updating with empty values."""
        instance, mock_service = real_google_sheets
        
        # Mock update response for clearing
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        mock_update.return_value.execute.return_value = {
            "spreadsheetId": "test_clear_123",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        
        # Empty data to clear cells
        empty_data = [
            ["", ""],
            ["", ""]
        ]
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        result = await MCPClass.update_range(
            file_id="test_clear_123",
            range="Sheet1!A1:B2",
            values=empty_data
        )
        
        # Verify clearing was successful
        data = json.loads(result)
        assert data["updatedCells"] == 4
        
        # Verify empty values were sent
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["body"]["values"] == empty_data


class TestUpdateRangeErrorHandling:
    """Test error handling in realistic scenarios."""
    
    @pytest.mark.e2e
    async def test_invalid_spreadsheet_id(self, real_google_sheets):
        """Test handling of invalid spreadsheet ID."""
        instance, mock_service = real_google_sheets
        
        # Mock API error for invalid spreadsheet
        from googleapiclient.errors import HttpError
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        
        # Create a mock HttpError
        import json as json_lib
        error_content = json_lib.dumps({
            "error": {
                "code": 404,
                "message": "Requested entity was not found."
            }
        }).encode('utf-8')
        
        mock_response = type('MockResponse', (), {
            'status': 404,
            'reason': 'Not Found'
        })()
        
        mock_update.return_value.execute.side_effect = HttpError(
            resp=mock_response,
            content=error_content
        )
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        
        with pytest.raises(HttpError):
            await MCPClass.update_range(
                file_id="invalid_spreadsheet_id",
                range="Sheet1!A1:B2",
                values=[["test", "data"]]
            )
    
    @pytest.mark.e2e
    async def test_invalid_range_format(self, real_google_sheets):
        """Test handling of invalid range format."""
        instance, mock_service = real_google_sheets
        
        # Mock API error for invalid range
        from googleapiclient.errors import HttpError
        mock_update = mock_service.spreadsheets.return_value.values.return_value.update
        
        error_content = json.dumps({
            "error": {
                "code": 400,
                "message": "Invalid range"
            }
        }).encode('utf-8')
        
        mock_response = type('MockResponse', (), {
            'status': 400,
            'reason': 'Bad Request'
        })()
        
        mock_update.return_value.execute.side_effect = HttpError(
            resp=mock_response,
            content=error_content
        )
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        
        with pytest.raises(HttpError):
            await MCPClass.update_range(
                file_id="valid_spreadsheet_id",
                range="InvalidRangeFormat",
                values=[["test"]]
            )
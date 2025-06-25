import pytest
from unittest.mock import Mock, patch
import json
from google_sheets import GoogleSheetsMCP, mcp

@pytest.fixture
def setup_mcp():
    """Setup MCP instance for testing"""
    with patch('google_sheets.os.path.exists', return_value=False):
        server = GoogleSheetsMCP(service_account_path="test_credentials.json")
        server.sheets_service = Mock()
        server.drive_service = Mock()
    
    # Store instance in mcp and clean up after
    original_instance = getattr(mcp, '_instance', None)
    mcp._instance = server
    
    yield server
    
    # Restore original instance
    if original_instance:
        mcp._instance = original_instance
    else:
        if hasattr(mcp, '_instance'):
            delattr(mcp, '_instance')

@pytest.mark.asyncio
async def test_create_sheet(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets(), 'create') as mock_create:
        mock_create.return_value.execute.return_value = {'spreadsheetId': 'test123'}
        result = await GoogleSheetsMCP.create_sheet("Test Sheet")
        assert json.loads(result)['spreadsheetId'] == 'test123'

@pytest.mark.asyncio
async def test_format_range(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets(), 'batchUpdate') as mock_update:
        mock_update.return_value.execute.return_value = {}
        result = await GoogleSheetsMCP.format_range(
            "test123",
            "Sheet1!A1:B10",
            {"backgroundColor": {"red": 1, "green": 0, "blue": 0}}
        )
        assert json.loads(result)['status'] == 'success'

@pytest.mark.asyncio
async def test_write_formula(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets().values(), 'update') as mock_update:
        mock_update.return_value.execute.return_value = {}
        result = await GoogleSheetsMCP.write_formula(
            "test123",
            "Sheet1!A1",
            "=SUM(A1:A10)"
        )
        assert json.loads(result)['status'] == 'success'

@pytest.mark.asyncio
async def test_add_sheet(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets(), 'batchUpdate') as mock_update:
        mock_update.return_value.execute.return_value = {}
        result = await GoogleSheetsMCP.add_sheet("test123", "New Sheet")
        assert json.loads(result)['status'] == 'success'

@pytest.mark.asyncio
async def test_delete_sheet(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets(), 'batchUpdate') as mock_update:
        mock_update.return_value.execute.return_value = {}
        result = await GoogleSheetsMCP.delete_sheet("test123", 0)
        assert json.loads(result)['status'] == 'success'

@pytest.mark.asyncio
async def test_get_sheet_properties(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets(), 'get') as mock_get:
        mock_get.return_value.execute.return_value = {
            'sheets': [
                {'properties': {'title': 'Sheet1', 'sheetId': 0}},
                {'properties': {'title': 'Sheet2', 'sheetId': 1}}
            ]
        }
        result = await GoogleSheetsMCP.get_sheet_properties("test123")
        sheets = json.loads(result)
        assert len(sheets) == 2
        assert sheets[0]['properties']['title'] == 'Sheet1'
        assert sheets[1]['properties']['title'] == 'Sheet2'

@pytest.mark.asyncio
async def test_list_files(setup_mcp):
    with patch.object(setup_mcp.drive_service.files(), 'list') as mock_list:
        mock_list.return_value.execute.return_value = {
            'files': [
                {
                    'id': '123',
                    'name': 'Test Sheet',
                    'createdTime': '2024-03-19T00:00:00Z',
                    'modifiedTime': '2024-03-19T00:00:00Z',
                    'owners': [{'emailAddress': 'test@example.com'}]
                }
            ]
        }
        files = await setup_mcp.list_files()
        assert len(files) == 1
        assert files[0].name == 'Test Sheet'
        assert str(files[0].uri) == 'sheets://123'

@pytest.mark.asyncio
async def test_read_file(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets().values(), 'get') as mock_get:
        mock_get.return_value.execute.return_value = {
            'values': [
                ['Header1', 'Header2'],
                ['Value1', 'Value2']
            ]
        }
        result = await setup_mcp.read_file("test123", {'headers': 'true'})
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]['Header1'] == 'Value1'
        assert data[0]['Header2'] == 'Value2'

@pytest.mark.asyncio
async def test_write_file(setup_mcp):
    with patch.object(setup_mcp.sheets_service.spreadsheets().values(), 'update') as mock_update:
        mock_update.return_value.execute.return_value = {
            'updatedCells': 2,
            'updatedRows': 1,
            'updatedColumns': 2,
            'updatedRange': 'Sheet1!A1:B1'
        }
        result = await setup_mcp.write_file(
            "test123",
            json.dumps([{'Header1': 'Value1', 'Header2': 'Value2'}])
        )
        data = json.loads(result)
        assert data['updated_cells'] == 2
        assert data['updated_rows'] == 1
        assert data['updated_columns'] == 2
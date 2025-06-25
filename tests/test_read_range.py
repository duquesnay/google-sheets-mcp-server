"""
Comprehensive tests for read_range functionality.
Tests include unit tests, integration tests, and validation of MCP protocol layer.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from google_sheets import GoogleSheetsMCP, mcp, GoogleSheetsError, SheetNotFoundError
from googleapiclient.errors import HttpError
from fastapi import HTTPException


class TestReadRangeUnit:
    """Unit tests for read_range functionality"""
    
    @pytest.fixture
    def mcp_server(self):
        """Create a GoogleSheetsMCP instance with mocked services"""
        with patch('google_sheets.os.path.exists', return_value=False):
            server = GoogleSheetsMCP(service_account_path="test_credentials.json")
            server.sheets_service = Mock()
            server.drive_service = Mock()
            return server
    
    @pytest.mark.asyncio
    async def test_read_range_simple(self, mcp_server):
        """Test reading a simple range"""
        # Mock the API response
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [
                ['A1', 'B1', 'C1'],
                ['A2', 'B2', 'C2'],
                ['A3', 'B3', 'C3']
            ],
            'range': 'Sheet1!A1:C3'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A1:C3")
        data = json.loads(result)
        
        assert 'values' in data
        assert len(data['values']) == 3
        assert data['values'][0] == ['A1', 'B1', 'C1']
        assert data['range'] == 'Sheet1!A1:C3'
    
    @pytest.mark.asyncio
    async def test_read_range_with_sheet_name(self, mcp_server):
        """Test reading a range with sheet name specified"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['Data']],
            'range': 'CustomSheet!A1:A1'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "CustomSheet!A1:A1")
        data = json.loads(result)
        
        assert data['values'] == [['Data']]
        assert data['range'] == 'CustomSheet!A1:A1'
        
        # Verify the API was called with correct parameters
        mock_values.get.assert_called_once()
        call_args = mock_values.get.call_args[1]
        assert call_args['spreadsheetId'] == 'test123'
        assert call_args['range'] == 'CustomSheet!A1:A1'
    
    @pytest.mark.asyncio
    async def test_read_range_empty_cells(self, mcp_server):
        """Test reading a range with empty cells"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [
                ['A1', '', 'C1'],
                ['', 'B2', ''],
                ['A3', 'B3', 'C3']
            ],
            'range': 'Sheet1!A1:C3'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A1:C3")
        data = json.loads(result)
        
        assert len(data['values']) == 3
        assert data['values'][0][1] == ''  # Empty cell
        assert data['values'][1][0] == ''  # Empty cell
    
    @pytest.mark.asyncio
    async def test_read_range_no_data(self, mcp_server):
        """Test reading an empty range"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'range': 'Sheet1!A1:C3'
            # Note: 'values' key is missing when range is empty
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A1:C3")
        data = json.loads(result)
        
        assert 'values' in data
        assert data['values'] == []
        assert data['range'] == 'Sheet1!A1:C3'
    
    @pytest.mark.asyncio
    async def test_read_range_different_data_types(self, mcp_server):
        """Test reading different data types (numbers, strings, booleans, dates)"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [
                ['String', 123, True, '2024-03-19'],
                ['Another', 456.78, False, '=SUM(A1:A2)']
            ],
            'range': 'Sheet1!A1:D2'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A1:D2")
        data = json.loads(result)
        
        assert data['values'][0][0] == 'String'
        assert data['values'][0][1] == 123
        assert data['values'][0][2] is True
        assert data['values'][1][3] == '=SUM(A1:A2)'
    
    @pytest.mark.asyncio
    async def test_read_range_invalid_range_format(self, mcp_server):
        """Test handling of invalid range formats"""
        mock_values = Mock()
        mock_error_resp = Mock()
        mock_error_resp.status = 400
        mock_error = HttpError(mock_error_resp, b'Invalid range')
        mock_values.get.return_value.execute.side_effect = mock_error
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        with pytest.raises(GoogleSheetsError) as exc_info:
            await mcp_server._read_range_impl("test123", "InvalidRange")
        
        assert "Invalid range" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_read_range_sheet_not_found(self, mcp_server):
        """Test handling when sheet doesn't exist"""
        mock_values = Mock()
        mock_error_resp = Mock()
        mock_error_resp.status = 404
        mock_error = HttpError(mock_error_resp, b'Sheet not found')
        mock_values.get.return_value.execute.side_effect = mock_error
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        with pytest.raises(SheetNotFoundError) as exc_info:
            await mcp_server._read_range_impl("test123", "NonExistent!A1:B2")
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_read_range_single_cell(self, mcp_server):
        """Test reading a single cell"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['Single Value']],
            'range': 'Sheet1!A1'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A1")
        data = json.loads(result)
        
        assert data['values'] == [['Single Value']]
        assert data['range'] == 'Sheet1!A1'
    
    @pytest.mark.asyncio
    async def test_read_range_entire_column(self, mcp_server):
        """Test reading an entire column"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['A1'], ['A2'], ['A3'], ['A4']],
            'range': 'Sheet1!A:A'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A:A")
        data = json.loads(result)
        
        assert len(data['values']) == 4
        assert all(len(row) == 1 for row in data['values'])
    
    @pytest.mark.asyncio
    async def test_read_range_entire_row(self, mcp_server):
        """Test reading an entire row"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['A1', 'B1', 'C1', 'D1']],
            'range': 'Sheet1!1:1'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "1:1")
        data = json.loads(result)
        
        assert len(data['values']) == 1
        assert len(data['values'][0]) == 4


class TestReadRangeMCPIntegration:
    """Integration tests for MCP handler"""
    
    @pytest.fixture
    def setup_mcp(self):
        """Setup MCP instance for testing"""
        with patch('google_sheets.os.path.exists', return_value=False):
            server = GoogleSheetsMCP(service_account_path="test_credentials.json")
            server.sheets_service = Mock()
            server.drive_service = Mock()
        
        # Store instance in mcp
        original_instance = getattr(mcp, '_instance', None)
        mcp._instance = server
        
        yield server
        
        # Restore original instance
        if original_instance:
            mcp._instance = original_instance
        else:
            delattr(mcp, '_instance')
    
    @pytest.mark.asyncio
    async def test_mcp_handler_returns_json_string(self, setup_mcp):
        """Test that MCP handler returns a JSON string, not an object"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['Test']],
            'range': 'Sheet1!A1'
        }
        setup_mcp.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Call the static MCP handler
        from google_sheets import GoogleSheetsMCP as MCPClass
        result = await MCPClass.read_range(file_id="test123", range="A1")
        
        # Verify it returns a string
        assert isinstance(result, str)
        
        # Verify it's valid JSON
        data = json.loads(result)
        assert 'values' in data
        assert data['values'] == [['Test']]
    
    @pytest.mark.asyncio
    async def test_mcp_handler_with_no_instance(self):
        """Test MCP handler behavior when no instance is set"""
        # Remove instance
        original_instance = getattr(mcp, '_instance', None)
        if hasattr(mcp, '_instance'):
            delattr(mcp, '_instance')
        
        try:
            # When no instance is set, we should get an AttributeError
            with pytest.raises(AttributeError) as exc_info:
                await GoogleSheetsMCP.read_range(file_id="test123", range="A1")
            assert "_instance" in str(exc_info.value)
        finally:
            # Restore instance
            if original_instance:
                mcp._instance = original_instance
    
    @pytest.mark.asyncio
    async def test_mcp_handler_parameter_validation(self, setup_mcp):
        """Test that MCP handler validates parameters properly"""
        # Test with missing file_id
        with pytest.raises(TypeError):
            await GoogleSheetsMCP.read_range(range="A1")
        
        # Test with missing range
        with pytest.raises(TypeError):
            await GoogleSheetsMCP.read_range(file_id="test123")
    
    @pytest.mark.asyncio
    async def test_mcp_handler_error_propagation(self, setup_mcp):
        """Test that errors are properly propagated through MCP handler"""
        mock_values = Mock()
        mock_error_resp = Mock()
        mock_error_resp.status = 403
        mock_error = HttpError(mock_error_resp, b'Access denied')
        mock_values.get.return_value.execute.side_effect = mock_error
        setup_mcp.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        with pytest.raises(GoogleSheetsError) as exc_info:
            await GoogleSheetsMCP.read_range(file_id="test123", range="A1")
        
        assert "403" in str(exc_info.value) or "Access denied" in str(exc_info.value)


class TestReadRangeEdgeCases:
    """Test edge cases and special scenarios"""
    
    @pytest.fixture
    def mcp_server(self):
        with patch('google_sheets.os.path.exists', return_value=False):
            server = GoogleSheetsMCP(service_account_path="test_credentials.json")
            server.sheets_service = Mock()
            server.drive_service = Mock()
            return server
    
    @pytest.mark.asyncio
    async def test_read_range_with_spaces_in_sheet_name(self, mcp_server):
        """Test reading from a sheet with spaces in the name"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['Data']],
            'range': "'My Sheet'!A1"
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "'My Sheet'!A1")
        data = json.loads(result)
        
        assert data['values'] == [['Data']]
        
        # Verify API was called with properly quoted sheet name
        call_args = mock_values.get.call_args[1]
        assert call_args['range'] == "'My Sheet'!A1"
    
    @pytest.mark.asyncio
    async def test_read_range_ragged_rows(self, mcp_server):
        """Test reading data with rows of different lengths"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [
                ['A1', 'B1', 'C1', 'D1'],
                ['A2', 'B2'],
                ['A3'],
                ['A4', 'B4', 'C4']
            ],
            'range': 'Sheet1!A1:D4'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "A1:D4")
        data = json.loads(result)
        
        assert len(data['values']) == 4
        assert len(data['values'][0]) == 4
        assert len(data['values'][1]) == 2
        assert len(data['values'][2]) == 1
        assert len(data['values'][3]) == 3
    
    @pytest.mark.asyncio
    async def test_read_range_formulas_vs_values(self, mcp_server):
        """Test reading formulas vs computed values"""
        mock_values = Mock()
        
        # Test with FORMULA value render option
        mock_values.get.return_value.execute.return_value = {
            'values': [['=SUM(A1:A10)', '=A1*2']],
            'range': 'Sheet1!B1:C1'
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        result = await mcp_server._read_range_impl("test123", "B1:C1", value_render_option="FORMULA")
        data = json.loads(result)
        
        assert data['values'][0][0] == '=SUM(A1:A10)'
        assert data['values'][0][1] == '=A1*2'
        
        # Verify API call included value_render_option
        call_args = mock_values.get.call_args[1]
        assert call_args['valueRenderOption'] == 'FORMULA'
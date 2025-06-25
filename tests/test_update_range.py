"""Tests for update_range functionality."""
import json
import pytest
from unittest.mock import Mock, patch
from google_sheets import GoogleSheetsMCP, mcp


@pytest.fixture
def mcp_server():
    """Create a GoogleSheetsMCP instance with mocked services"""
    with patch('google_sheets.os.path.exists', return_value=False):
        server = GoogleSheetsMCP(service_account_path="test_credentials.json")
        server.sheets_service = Mock()
        server.drive_service = Mock()
        # Store instance in mcp module for static handlers
        mcp._instance = server
        return server


class TestUpdateRange:
    """Test update_range method."""
    
    @pytest.mark.asyncio
    async def test_update_range_basic(self, mcp_server):
        """Test basic range update with 2D array."""
        # Mock the API response
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Test data
        values = [
            ["Name", "Age"],
            ["Alice", "30"]
        ]
        
        # Call the method
        result = await mcp_server._update_range_impl(
            "test123",
            "Sheet1!A1:B2",
            values
        )
        
        # Verify the result
        assert result["spreadsheetId"] == "test123"
        assert result["updatedRange"] == "Sheet1!A1:B2"
        assert result["updatedCells"] == 4
        
        # Verify API was called correctly
        mock_values.update.assert_called_once()
        call_args = mock_values.update.call_args
        assert call_args[1]["spreadsheetId"] == "test123"
        assert call_args[1]["range"] == "Sheet1!A1:B2"
        assert call_args[1]["body"]["values"] == values
        assert call_args[1]["valueInputOption"] == "USER_ENTERED"
    
    @pytest.mark.asyncio
    async def test_update_range_with_formulas(self, mcp_server):
        """Test updating range with formulas."""
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1:A3",
            "updatedRows": 3,
            "updatedColumns": 1,
            "updatedCells": 3
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Test data with formulas
        values = [
            ["=SUM(B1:B10)"],
            ["=AVERAGE(B1:B10)"],
            ["=COUNT(B1:B10)"]
        ]
        
        result = await mcp_server._update_range_impl(
            "test123",
            "Sheet1!A1:A3",
            values,
            value_input_option="USER_ENTERED"
        )
        
        assert result["updatedCells"] == 3
        
        # Verify formulas were sent with USER_ENTERED option
        call_args = mock_values.update.call_args
        assert call_args[1]["valueInputOption"] == "USER_ENTERED"
        assert call_args[1]["body"]["values"] == values
    
    @pytest.mark.asyncio
    async def test_update_range_raw_input(self, mcp_server):
        """Test updating range with RAW input option."""
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1:A2",
            "updatedRows": 2,
            "updatedColumns": 1,
            "updatedCells": 2
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Test data that should be treated as raw strings
        values = [
            ["=SUM(1,2)"],  # Should be stored as string, not formula
            ["123"]
        ]
        
        result = await mcp_server._update_range_impl(
            "test123",
            "Sheet1!A1:A2",
            values,
            value_input_option="RAW"
        )
        
        assert result["updatedCells"] == 2
        
        # Verify RAW option was used
        call_args = mock_values.update.call_args
        assert call_args[1]["valueInputOption"] == "RAW"
    
    @pytest.mark.asyncio
    async def test_update_single_cell(self, mcp_server):
        """Test updating a single cell."""
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1",
            "updatedRows": 1,
            "updatedColumns": 1,
            "updatedCells": 1
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        values = [["Hello World"]]
        
        result = await mcp_server._update_range_impl(
            "test123",
            "Sheet1!A1",
            values
        )
        
        assert result["updatedCells"] == 1
        assert result["updatedRange"] == "Sheet1!A1"
    
    @pytest.mark.asyncio
    async def test_update_range_with_empty_values(self, mcp_server):
        """Test updating range with empty values to clear cells."""
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Empty values to clear cells
        values = [
            ["", ""],
            ["", ""]
        ]
        
        result = await mcp_server._update_range_impl(
            "test123",
            "Sheet1!A1:B2",
            values
        )
        
        assert result["updatedCells"] == 4
        
        # Verify empty values were sent
        call_args = mock_values.update.call_args
        assert call_args[1]["body"]["values"] == values
    
    @pytest.mark.asyncio
    async def test_update_range_mixed_types(self, mcp_server):
        """Test updating range with mixed data types."""
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1:C3",
            "updatedRows": 3,
            "updatedColumns": 3,
            "updatedCells": 9
        }
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Mixed types: strings, numbers, booleans, formulas
        values = [
            ["Name", "Score", "Passed"],
            ["Alice", 95, True],
            ["Bob", 78, False]
        ]
        
        result = await mcp_server._update_range_impl(
            "test123",
            "Sheet1!A1:C3",
            values
        )
        
        assert result["updatedCells"] == 9
        
        # Verify values were sent (they'll be converted to strings by the API)
        call_args = mock_values.update.call_args
        expected_values = [
            ["Name", "Score", "Passed"],
            ["Alice", "95", "TRUE"],  # Numbers and booleans converted to strings
            ["Bob", "78", "FALSE"]
        ]
        assert call_args[1]["body"]["values"] == expected_values
    
    @pytest.mark.asyncio
    async def test_update_range_validation_empty_values(self, mcp_server):
        """Test that empty values array raises ValueError."""
        with pytest.raises(ValueError, match="Values array cannot be empty"):
            await mcp_server._update_range_impl(
                "test123",
                "Sheet1!A1:B2",
                []
            )
    
    @pytest.mark.asyncio
    async def test_update_range_validation_empty_rows(self, mcp_server):
        """Test that empty rows raise ValueError."""
        with pytest.raises(ValueError, match="Values array cannot contain empty rows"):
            await mcp_server._update_range_impl(
                "test123",
                "Sheet1!A1:B2",
                [[]]
            )
    
    @pytest.mark.asyncio
    async def test_update_range_validation_inconsistent_columns(self, mcp_server):
        """Test that inconsistent column counts raise ValueError."""
        values = [
            ["A", "B", "C"],
            ["D", "E"]  # Missing one column
        ]
        
        with pytest.raises(ValueError, match="All rows must have the same number of columns"):
            await mcp_server._update_range_impl(
                "test123",
                "Sheet1!A1:C2",
                values
            )
    
    @pytest.mark.asyncio
    async def test_update_range_api_error(self, mcp_server):
        """Test handling of API errors."""
        mock_values = Mock()
        mock_values.update.return_value.execute.side_effect = Exception("API Error: Invalid range")
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        with pytest.raises(Exception, match="API Error: Invalid range"):
            await mcp_server._update_range_impl(
                "test123",
                "InvalidRange",
                [["value"]]
            )


class TestUpdateRangeMCPHandler:
    """Test the MCP handler for update_range."""
    
    @pytest.mark.asyncio
    async def test_mcp_handler_basic(self, mcp_server):
        """Test MCP handler with basic update."""
        # Mock the instance method
        mock_result = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1:B2",
            "updatedRows": 2,
            "updatedColumns": 2,
            "updatedCells": 4
        }
        
        # Mock the actual API call
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = mock_result
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        # Call the static MCP handler
        from google_sheets import GoogleSheetsMCP as MCPClass
        result = await MCPClass.update_range(
            file_id="test123",
            range="Sheet1!A1:B2",
            values=[["A", "B"], ["C", "D"]]
        )
        
        # Result should be JSON string
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["updatedCells"] == 4
        
        # Verify API was called with correct args
        mock_values.update.assert_called_once()
        call_args = mock_values.update.call_args
        assert call_args[1]["spreadsheetId"] == "test123"
        assert call_args[1]["range"] == "Sheet1!A1:B2"
        assert call_args[1]["valueInputOption"] == "USER_ENTERED"
    
    @pytest.mark.asyncio
    async def test_mcp_handler_with_raw_option(self, mcp_server):
        """Test MCP handler with RAW input option."""
        mock_result = {
            "spreadsheetId": "test123",
            "updatedRange": "Sheet1!A1",
            "updatedRows": 1,
            "updatedColumns": 1,
            "updatedCells": 1
        }
        
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = mock_result
        mcp_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
        
        from google_sheets import GoogleSheetsMCP as MCPClass
        
        result = await MCPClass.update_range(
            file_id="test123",
            range="Sheet1!A1",
            values=[["=SUM(1,2)"]],
            value_input_option="RAW"
        )
        
        parsed = json.loads(result)
        assert parsed["updatedCells"] == 1
        
        # Verify RAW option was passed
        call_args = mock_values.update.call_args
        assert call_args[1]["valueInputOption"] == "RAW"
    
    @pytest.mark.asyncio
    async def test_mcp_handler_validation_error(self, mcp_server):
        """Test MCP handler with validation error."""
        from google_sheets import GoogleSheetsMCP as MCPClass
        
        with pytest.raises(ValueError, match="Values array cannot be empty"):
            await MCPClass.update_range(
                file_id="test123",
                range="Sheet1!A1:B2",
                values=[]
            )
    
    @pytest.mark.asyncio
    async def test_mcp_handler_missing_required_fields(self):
        """Test MCP handler with missing required fields."""
        from google_sheets import GoogleSheetsMCP as MCPClass
        
        # Missing file_id
        with pytest.raises(TypeError):
            await MCPClass.update_range(
                range="Sheet1!A1",
                values=[["test"]]
            )
        
        # Missing range
        with pytest.raises(TypeError):
            await MCPClass.update_range(
                file_id="test123",
                values=[["test"]]
            )
        
        # Missing values
        with pytest.raises(TypeError):
            await MCPClass.update_range(
                file_id="test123",
                range="Sheet1!A1"
            )
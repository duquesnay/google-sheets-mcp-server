"""
End-to-end tests for read_range functionality.
These tests require actual Google Sheets API access.
"""
import pytest
import json
import os
import asyncio
from google_sheets import GoogleSheetsMCP, mcp


@pytest.mark.skipif(
    not os.path.exists(os.path.expanduser("~/.config/google_sheets_mcp/test-service-account.json")),
    reason="No test service account credentials found"
)
class TestReadRangeE2E:
    """End-to-end tests that use real Google Sheets API"""
    
    @pytest.fixture
    async def setup_test_sheet(self):
        """Create a test sheet with sample data"""
        # Initialize server with test credentials
        service_account_path = os.path.expanduser("~/.config/google_sheets_mcp/test-service-account.json")
        server = GoogleSheetsMCP(service_account_path=service_account_path)
        mcp._instance = server
        
        # Create a test spreadsheet
        create_result = await GoogleSheetsMCP.create_sheet("Test Read Range E2E")
        sheet_data = json.loads(create_result)
        sheet_id = sheet_data['spreadsheetId']
        
        # Populate with test data
        test_data = [
            ['Name', 'Age', 'City', 'Score'],
            ['Alice', 25, 'New York', 95.5],
            ['Bob', 30, 'San Francisco', 87.3],
            ['Charlie', 28, 'Chicago', 92.0],
            ['', '', '', ''],  # Empty row
            ['David', 35, 'Austin', 88.9]
        ]
        
        # Write test data
        await server.write_file(
            sheet_id,
            json.dumps(test_data)
        )
        
        # Add a second sheet with different data
        await GoogleSheetsMCP.add_sheet(sheet_id, "Sheet2")
        
        # Write data to second sheet
        sheet2_data = [
            ['Product', 'Price', 'Quantity'],
            ['Apple', 1.50, 100],
            ['Banana', 0.75, 150],
            ['Orange', 2.00, 80]
        ]
        
        await server.write_file(
            f"{sheet_id}/Sheet2/A1",
            json.dumps(sheet2_data)
        )
        
        # Add formulas to test formula reading
        await GoogleSheetsMCP.write_formula(sheet_id, "Sheet1!E1", "Total")
        await GoogleSheetsMCP.write_formula(sheet_id, "Sheet1!E2", "=D2")
        await GoogleSheetsMCP.write_formula(sheet_id, "Sheet1!E3", "=D3")
        await GoogleSheetsMCP.write_formula(sheet_id, "Sheet1!E4", "=D4")
        await GoogleSheetsMCP.write_formula(sheet_id, "Sheet1!E6", "=SUM(D2:D4)")
        
        yield sheet_id, server
        
        # Cleanup: Delete the test sheet
        try:
            # Note: This would require implementing a delete_spreadsheet method
            # For now, we'll leave it for manual cleanup
            print(f"\nTest sheet created: {sheet_id}")
            print("Please delete manually if needed")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    @pytest.mark.asyncio
    async def test_read_basic_range(self, setup_test_sheet):
        """Test reading a basic range from the test sheet"""
        sheet_id, server = setup_test_sheet
        
        result = await GoogleSheetsMCP.read_range(sheet_id, "A1:D4")
        data = json.loads(result)
        
        assert 'values' in data
        assert 'range' in data
        assert len(data['values']) == 4
        assert data['values'][0] == ['Name', 'Age', 'City', 'Score']
        assert data['values'][1][0] == 'Alice'
        assert data['values'][1][1] == 25
        assert data['values'][1][3] == 95.5
    
    @pytest.mark.asyncio
    async def test_read_single_cell(self, setup_test_sheet):
        """Test reading a single cell"""
        sheet_id, server = setup_test_sheet
        
        result = await GoogleSheetsMCP.read_range(sheet_id, "B2")
        data = json.loads(result)
        
        assert data['values'] == [[25]]
    
    @pytest.mark.asyncio
    async def test_read_empty_range(self, setup_test_sheet):
        """Test reading an empty range"""
        sheet_id, server = setup_test_sheet
        
        result = await GoogleSheetsMCP.read_range(sheet_id, "A5:D5")
        data = json.loads(result)
        
        # Empty cells should return empty strings
        assert data['values'] == [['', '', '', '']]
    
    @pytest.mark.asyncio
    async def test_read_from_named_sheet(self, setup_test_sheet):
        """Test reading from a specific sheet by name"""
        sheet_id, server = setup_test_sheet
        
        result = await GoogleSheetsMCP.read_range(sheet_id, "Sheet2!A1:C2")
        data = json.loads(result)
        
        assert len(data['values']) == 2
        assert data['values'][0] == ['Product', 'Price', 'Quantity']
        assert data['values'][1] == ['Apple', 1.5, 100]
    
    @pytest.mark.asyncio
    async def test_read_entire_column(self, setup_test_sheet):
        """Test reading an entire column"""
        sheet_id, server = setup_test_sheet
        
        result = await GoogleSheetsMCP.read_range(sheet_id, "A:A")
        data = json.loads(result)
        
        # Should get all non-empty cells in column A
        assert len(data['values']) >= 5
        assert data['values'][0] == ['Name']
        assert data['values'][1] == ['Alice']
    
    @pytest.mark.asyncio
    async def test_read_formulas(self, setup_test_sheet):
        """Test reading formulas vs values"""
        sheet_id, server = setup_test_sheet
        
        # Read computed values (default)
        result_values = await GoogleSheetsMCP.read_range(sheet_id, "E1:E6")
        data_values = json.loads(result_values)
        
        # Read formulas
        result_formulas = await GoogleSheetsMCP.read_range(
            sheet_id, 
            "E1:E6",
            value_render_option="FORMULA"
        )
        data_formulas = json.loads(result_formulas)
        
        # Check computed values
        assert data_values['values'][0] == ['Total']
        assert data_values['values'][1] == [95.5]
        assert data_values['values'][5] == [274.8]  # Sum of scores
        
        # Check formulas
        assert data_formulas['values'][0] == ['Total']
        assert data_formulas['values'][1] == ['=D2']
        assert data_formulas['values'][5] == ['=SUM(D2:D4)']
    
    @pytest.mark.asyncio
    async def test_read_invalid_range(self, setup_test_sheet):
        """Test error handling for invalid range"""
        sheet_id, server = setup_test_sheet
        
        with pytest.raises(Exception) as exc_info:
            await GoogleSheetsMCP.read_range(sheet_id, "InvalidRange!")
        
        assert "400" in str(exc_info.value) or "Invalid" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_read_non_existent_sheet(self, setup_test_sheet):
        """Test error handling for non-existent sheet"""
        sheet_id, server = setup_test_sheet
        
        with pytest.raises(Exception) as exc_info:
            await GoogleSheetsMCP.read_range(sheet_id, "NonExistentSheet!A1:B2")
        
        assert "400" in str(exc_info.value) or "Unable to parse range" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_read_multiple_ranges_sequentially(self, setup_test_sheet):
        """Test reading multiple ranges in sequence"""
        sheet_id, server = setup_test_sheet
        
        # Read headers
        headers_result = await GoogleSheetsMCP.read_range(sheet_id, "A1:D1")
        headers = json.loads(headers_result)['values'][0]
        
        # Read data rows
        data_result = await GoogleSheetsMCP.read_range(sheet_id, "A2:D6")
        data_rows = json.loads(data_result)['values']
        
        assert headers == ['Name', 'Age', 'City', 'Score']
        assert len(data_rows) == 5
        assert data_rows[0][0] == 'Alice'
        assert data_rows[4][0] == 'David'


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
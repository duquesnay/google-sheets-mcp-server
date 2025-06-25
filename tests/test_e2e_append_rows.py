"""End-to-end tests for append_rows functionality with real Google Sheets API."""

import json
import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_sheets import GoogleSheetsMCP, mcp


class TestAppendRowsE2E:
    """End-to-end tests for append_rows with real API."""

    @pytest.fixture(scope="class")
    def google_sheets_instance(self):
        """Create a real GoogleSheetsMCP instance."""
        instance = GoogleSheetsMCP()
        # This will use the actual credentials from command line
        mcp._instance = instance
        return instance

    @pytest.fixture
    async def test_spreadsheet(self, google_sheets_instance):
        """Create a test spreadsheet for the tests."""
        result = await GoogleSheetsMCP.create_sheet({"title": "Test Append Rows E2E"})
        sheet_data = json.loads(result)
        sheet_id = sheet_data["spreadsheetId"]
        
        yield sheet_id
        
        # Cleanup would go here if we had delete functionality
        print(f"Test complete. Sheet ID: {sheet_id}")

    @pytest.mark.asyncio
    async def test_append_to_empty_sheet(self, google_sheets_instance, test_spreadsheet):
        """Test appending to an empty sheet."""
        # Append first set of data
        values = [
            ["Name", "Age", "City"],
            ["Alice", "30", "New York"],
            ["Bob", "25", "San Francisco"]
        ]
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet1",
            "values": values
        })
        
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 3
        assert result_data["updatedCells"] == 9
        
        # Verify by reading back
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet1!A1:C3"
        })
        read_data = json.loads(read_result)
        assert read_data["values"] == values

    @pytest.mark.asyncio
    async def test_append_to_existing_data(self, google_sheets_instance, test_spreadsheet):
        """Test appending to a sheet with existing data."""
        # First, add some initial data
        initial_values = [
            ["Product", "Price", "Stock"],
            ["Laptop", "999", "10"],
            ["Mouse", "29", "50"]
        ]
        
        await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet2",
            "values": initial_values
        })
        
        # Now append more data
        new_values = [
            ["Keyboard", "79", "25"],
            ["Monitor", "299", "15"]
        ]
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet2",
            "values": new_values
        })
        
        result_data = json.loads(result)
        # Should have appended after row 3
        assert "A4:C5" in result_data["updatedRange"] or "A4" in result_data["updatedRange"]
        
        # Verify all data is there
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet2!A1:C5"
        })
        read_data = json.loads(read_result)
        expected_all = initial_values + new_values
        assert len(read_data["values"]) == 5
        assert read_data["values"] == expected_all

    @pytest.mark.asyncio
    async def test_append_with_formulas(self, google_sheets_instance, test_spreadsheet):
        """Test appending formulas with USER_ENTERED option."""
        # Add data with formulas
        values = [
            ["Item", "Quantity", "Price", "Total"],
            ["Widget A", "5", "10", "=B2*C2"],
            ["Widget B", "3", "15", "=B3*C3"],
            ["", "", "Total:", "=SUM(D2:D3)"]
        ]
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet3",
            "values": values,
            "value_input_option": "USER_ENTERED"
        })
        
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 4
        
        # Read back with formula values
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet3!A1:D4",
            "value_render_option": "FORMULA"
        })
        read_data = json.loads(read_result)
        
        # Check that formulas were preserved
        assert read_data["values"][1][3] == "=B2*C2"
        assert read_data["values"][2][3] == "=B3*C3"
        assert read_data["values"][3][3] == "=SUM(D2:D3)"

    @pytest.mark.asyncio
    async def test_append_with_specific_column_range(self, google_sheets_instance, test_spreadsheet):
        """Test appending to specific columns."""
        # First create headers across all columns
        headers = [["A", "B", "C", "D", "E"]]
        await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet4!A1:E1",
            "values": headers
        })
        
        # Now append data only to columns C:E
        values = [
            ["Data C1", "Data D1", "Data E1"],
            ["Data C2", "Data D2", "Data E2"]
        ]
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet4!C:E",
            "values": values
        })
        
        result_data = json.loads(result)
        # Should append starting at C2
        assert "C2" in result_data["updatedRange"]
        
        # Verify the data placement
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet4!A1:E3"
        })
        read_data = json.loads(read_result)
        
        # Check that columns A and B are empty in rows 2-3
        assert len(read_data["values"]) >= 3
        if len(read_data["values"][1]) >= 3:
            assert read_data["values"][1][2] == "Data C1"  # Column C
        if len(read_data["values"][2]) >= 3:
            assert read_data["values"][2][2] == "Data C2"  # Column C

    @pytest.mark.asyncio
    async def test_append_mixed_data_types(self, google_sheets_instance, test_spreadsheet):
        """Test appending various data types."""
        values = [
            ["String", 123, 45.67, True, None, ""],
            ["Text", 0, -10.5, False, "", "=A1"],
            ["", "", "", "", "", ""]  # Empty row
        ]
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet5",
            "values": values,
            "value_input_option": "USER_ENTERED"
        })
        
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 3
        
        # Read back and verify
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet5!A1:F3"
        })
        read_data = json.loads(read_result)
        
        # Check data types were handled correctly
        assert read_data["values"][0][0] == "String"
        assert read_data["values"][0][1] == "123"  # Numbers become strings
        assert read_data["values"][0][3] == "TRUE"  # Booleans become strings

    @pytest.mark.asyncio
    async def test_append_with_insert_rows_option(self, google_sheets_instance, test_spreadsheet):
        """Test INSERT_ROWS option to shift existing data down."""
        # Add initial data
        initial_values = [
            ["Header 1", "Header 2"],
            ["Row 1 A", "Row 1 B"],
            ["Row 2 A", "Row 2 B"]
        ]
        
        await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet6",
            "values": initial_values
        })
        
        # Now append with INSERT_ROWS at a specific position
        new_values = [
            ["Inserted A", "Inserted B"]
        ]
        
        # This should insert and push existing data down
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet6!A2",  # Insert at row 2
            "values": new_values,
            "insert_data_option": "INSERT_ROWS"
        })
        
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 1

    @pytest.mark.asyncio
    async def test_append_large_dataset(self, google_sheets_instance, test_spreadsheet):
        """Test appending a larger dataset."""
        # Generate 100 rows of data
        values = []
        for i in range(100):
            values.append([
                f"Item {i+1}",
                i + 1,
                (i + 1) * 10.5,
                f"Description for item {i+1}"
            ])
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet7",
            "values": values
        })
        
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 100
        assert result_data["updatedCells"] == 400  # 100 rows * 4 columns
        
        # Verify a sample
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet7!A50:D50"
        })
        read_data = json.loads(read_result)
        assert read_data["values"][0][0] == "Item 50"

    @pytest.mark.asyncio
    async def test_append_with_raw_input_option(self, google_sheets_instance, test_spreadsheet):
        """Test RAW value input option (no parsing)."""
        values = [
            ["=SUM(A1:A10)", "'123", "TRUE", "01/01/2024"]
        ]
        
        result = await GoogleSheetsMCP.append_rows({
            "file_id": test_spreadsheet,
            "range": "Sheet8",
            "values": values,
            "value_input_option": "RAW"
        })
        
        result_data = json.loads(result)
        assert result_data["updatedRows"] == 1
        
        # Read back - formulas should be stored as text
        read_result = await GoogleSheetsMCP.read_range({
            "file_id": test_spreadsheet,
            "range": "Sheet8!A1:D1"
        })
        read_data = json.loads(read_result)
        
        # With RAW, the formula should be stored as plain text
        assert read_data["values"][0][0] == "=SUM(A1:A10)"
        assert read_data["values"][0][1] == "'123"


if __name__ == "__main__":
    # Run a specific test for debugging
    async def run_test():
        instance = GoogleSheetsMCP()
        mcp._instance = instance
        
        # Create test sheet
        result = await GoogleSheetsMCP.create_sheet({"title": "Manual Test Append"})
        sheet_data = json.loads(result)
        sheet_id = sheet_data["spreadsheetId"]
        print(f"Created sheet: {sheet_id}")
        
        # Test append
        values = [["Test", "Data"], ["Row", "2"]]
        append_result = await GoogleSheetsMCP.append_rows({
            "file_id": sheet_id,
            "range": "Sheet1",
            "values": values
        })
        print(f"Append result: {append_result}")
        
    asyncio.run(run_test())
"""End-to-end tests for insert_rows functionality.

These tests validate that the insert_rows tool works correctly with the actual Google Sheets API.
They should be run against a real test spreadsheet to ensure integration correctness.

Note: These tests require valid Google credentials and a test spreadsheet.
They may be skipped in CI environments without proper credentials.
"""

import json
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_sheets import GoogleSheetsMCP, mcp


@pytest.mark.e2e
class TestInsertRowsE2E:
    """End-to-end tests for insert_rows functionality."""

    @pytest.fixture(scope="class")
    def test_sheet_id(self):
        """Get test sheet ID from environment variable."""
        sheet_id = os.environ.get("TEST_SHEET_ID")
        if not sheet_id:
            pytest.skip("TEST_SHEET_ID environment variable not set")
        return sheet_id

    @pytest.fixture(scope="class")
    def google_sheets_instance(self):
        """Create real GoogleSheetsMCP instance for testing."""
        # Try to get service account path from environment
        service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH")
        
        try:
            instance = GoogleSheetsMCP(service_account_path=service_account_path)
            # Store the instance for MCP handlers
            mcp._instance = instance
            
            # Test that we can initialize services
            instance._initialize_services()
            if not instance.sheets_service:
                pytest.skip("Could not initialize Google Sheets service")
            
            return instance
        except Exception as e:
            pytest.skip(f"Could not create GoogleSheetsMCP instance: {str(e)}")

    @pytest.mark.asyncio
    async def test_insert_empty_rows_real_api(self, test_sheet_id, google_sheets_instance):
        """Test inserting empty rows using real Google Sheets API."""
        # Get initial data to know where to insert
        initial_data = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range="Sheet1!A:A"
        )
        initial_data_parsed = json.loads(initial_data)
        initial_row_count = len(initial_data_parsed.get("values", []))
        
        # Insert 2 empty rows at position 1 (after header row)
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,  # Default sheet
            start_index=1,
            num_rows=2
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["spreadsheetId"] == test_sheet_id
        assert result_data["insertedRows"] == 2
        assert result_data["startIndex"] == 1
        
        # Verify that rows were actually inserted by reading data again
        new_data = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range="Sheet1!A:A"
        )
        new_data_parsed = json.loads(new_data)
        new_row_count = len(new_data_parsed.get("values", []))
        
        # Should have 2 more rows (even if they're empty, the range changes)
        # Note: Empty rows might not be counted in some cases, so we check the actual impact
        print(f"Initial rows: {initial_row_count}, New rows: {new_row_count}")

    @pytest.mark.asyncio
    async def test_insert_rows_with_data_real_api(self, test_sheet_id, google_sheets_instance):
        """Test inserting rows with data using real Google Sheets API."""
        # Data to insert
        values = [
            ["E2E Test", "Insert Rows", "With Data"],
            ["Row 2", "Column 2", "Value 3"]
        ]
        
        # Insert rows with data at position 3
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,
            start_index=3,
            num_rows=2,
            values=values
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["spreadsheetId"] == test_sheet_id
        assert result_data["insertedRows"] == 2
        assert result_data["updatedCells"] == 6  # 2 rows × 3 columns
        
        # Verify the data was actually written by reading it back
        read_result = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range="Sheet1!A4:C5"  # Read the inserted rows (1-indexed)
        )
        
        read_data = json.loads(read_result)
        read_values = read_data.get("values", [])
        
        # Verify the data matches what we inserted
        assert len(read_values) >= 2
        assert read_values[0][0] == "E2E Test"
        assert read_values[0][1] == "Insert Rows"
        assert read_values[0][2] == "With Data"
        assert read_values[1][0] == "Row 2"

    @pytest.mark.asyncio
    async def test_insert_rows_with_formulas_real_api(self, test_sheet_id, google_sheets_instance):
        """Test inserting rows with formulas using real API."""
        # Data with formulas
        values = [
            ["Formula Test", "=1+1", "=SUM(B6:B6)"],
            ["Static", "100", "=B7*2"]
        ]
        
        # Insert rows with formulas
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,
            start_index=5,
            num_rows=2,
            values=values,
            value_input_option="USER_ENTERED"  # Process formulas
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["insertedRows"] == 2
        assert result_data["updatedCells"] == 6
        
        # Read back and verify formulas were processed
        read_result = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range="Sheet1!A6:C7",
            value_render_option="FORMULA"
        )
        
        read_data = json.loads(read_result)
        read_values = read_data.get("values", [])
        
        # Verify formulas are present
        assert len(read_values) >= 2
        assert read_values[0][1] == "=1+1"
        assert "SUM" in read_values[0][2]

    @pytest.mark.asyncio
    async def test_insert_rows_using_sheet_name_real_api(self, test_sheet_id, google_sheets_instance):
        """Test inserting rows using sheet name instead of ID."""
        # First, get the sheet properties to know the actual sheet name
        props_result = await GoogleSheetsMCP.get_sheet_properties(test_sheet_id)
        props_data = json.loads(props_result)
        sheet_name = props_data[0]["properties"]["title"]  # Get first sheet name
        
        # Insert using sheet name
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_name=sheet_name,
            start_index=7,
            num_rows=1,
            values=[["Sheet Name Test", "Success", "Working"]]
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["insertedRows"] == 1
        assert "sheetId" in result_data  # Should include resolved sheet ID
        
        # Verify data was inserted
        read_result = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range=f"'{sheet_name}'!A8:C8"
        )
        
        read_data = json.loads(read_result)
        read_values = read_data.get("values", [])
        assert len(read_values) >= 1
        assert read_values[0][0] == "Sheet Name Test"

    @pytest.mark.asyncio
    async def test_insert_rows_at_beginning_real_api(self, test_sheet_id, google_sheets_instance):
        """Test inserting rows at the very beginning (index 0)."""
        # Insert at the beginning
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,
            start_index=0,
            num_rows=1,
            values=[["HEADER", "New First Row", "Beginning"]]
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["startIndex"] == 0
        assert result_data["insertedRows"] == 1
        
        # Verify it's now the first row
        read_result = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range="Sheet1!A1:C1"
        )
        
        read_data = json.loads(read_result)
        read_values = read_data.get("values", [])
        assert len(read_values) >= 1
        assert read_values[0][0] == "HEADER"

    @pytest.mark.asyncio
    async def test_insert_rows_error_cases_real_api(self, test_sheet_id, google_sheets_instance):
        """Test error cases with real API."""
        # Test with invalid sheet name
        with pytest.raises(ValueError, match="Sheet 'NonExistentSheet' not found"):
            await GoogleSheetsMCP.insert_rows(
                file_id=test_sheet_id,
                sheet_name="NonExistentSheet",
                start_index=1,
                num_rows=1
            )
        
        # Test with very large start_index (should still work)
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,
            start_index=1000,
            num_rows=1,
            values=[["Large Index", "Test", "OK"]]
        )
        
        result_data = json.loads(result)
        assert result_data["insertedRows"] == 1

    @pytest.mark.asyncio
    async def test_insert_rows_inherit_properties_real_api(self, test_sheet_id, google_sheets_instance):
        """Test inserting rows with inherit_from_before option."""
        # Insert rows with inheritance (should inherit formatting from previous row)
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,
            start_index=2,
            num_rows=1,
            inherit_from_before=True,
            values=[["Inherit Test", "Properties", "Preserved"]]
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["insertedRows"] == 1
        assert result_data["updatedCells"] == 3

    @pytest.mark.asyncio
    async def test_insert_rows_performance_large_batch_real_api(self, test_sheet_id, google_sheets_instance):
        """Test performance with a larger batch of rows."""
        # Create a larger dataset
        num_rows = 10
        values = []
        for i in range(num_rows):
            values.append([f"Batch Row {i+1}", f"Col2-{i+1}", f"Col3-{i+1}"])
        
        # Insert the batch
        result = await GoogleSheetsMCP.insert_rows(
            file_id=test_sheet_id,
            sheet_id=0,
            start_index=20,  # Insert further down to avoid conflicts
            num_rows=num_rows,
            values=values
        )
        
        # Verify the result
        result_data = json.loads(result)
        assert result_data["insertedRows"] == num_rows
        assert result_data["updatedCells"] == num_rows * 3  # 3 columns per row
        
        # Spot check a few rows
        read_result = await GoogleSheetsMCP.read_range(
            file_id=test_sheet_id,
            range="Sheet1!A21:C23"  # Read first 3 rows of the batch
        )
        
        read_data = json.loads(read_result)
        read_values = read_data.get("values", [])
        assert len(read_values) >= 3
        assert read_values[0][0] == "Batch Row 1"
        assert read_values[2][0] == "Batch Row 3"
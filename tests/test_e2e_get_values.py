"""End-to-end tests for get_values functionality with real Google Sheets API."""

import json
import os
import pytest
from google_sheets import GoogleSheetsMCP, mcp


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_SHEETS_TEST_SPREADSHEET_ID"),
    reason="GOOGLE_SHEETS_TEST_SPREADSHEET_ID environment variable not set"
)
class TestE2EGetValues:
    """End-to-end tests for get_values with real Google Sheets API."""

    @pytest.fixture
    def test_spreadsheet_id(self):
        """Get test spreadsheet ID from environment."""
        return os.environ["GOOGLE_SHEETS_TEST_SPREADSHEET_ID"]

    @pytest.fixture
    def credentials_path(self):
        """Get credentials path from environment."""
        return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    @pytest.fixture
    async def setup_mcp_instance(self, credentials_path):
        """Set up the MCP instance with real credentials."""
        if not credentials_path:
            pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set")
        
        # Initialize the MCP instance
        instance = GoogleSheetsMCP()
        await instance.initialize(credentials_path=credentials_path)
        
        # Set the global instance
        mcp._instance = instance
        
        yield instance
        
        # Cleanup
        mcp._instance = None

    @pytest.mark.asyncio
    async def test_e2e_get_values_single_range(self, setup_mcp_instance, test_spreadsheet_id):
        """Test getting values from a single range with real API."""
        # Prepare test data first
        instance = setup_mcp_instance
        
        # Write some test data
        update_body = {
            "values": [
                ["Test Name", "Test Value", "Test Date"],
                ["Alice", "100", "2024-01-01"],
                ["Bob", "200", "2024-01-02"]
            ]
        }
        
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!A1:C3",
            valueInputOption="USER_ENTERED",
            body=update_body
        ).execute()

        # Test get_values
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": "Sheet1!A1:C3"
        })

        # Verify result
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["spreadsheetId"] == test_spreadsheet_id
        assert len(data["valueRanges"]) == 1
        
        value_range = data["valueRanges"][0]
        assert "Sheet1!A1:C3" in value_range["range"]
        assert len(value_range["values"]) == 3
        assert value_range["values"][0] == ["Test Name", "Test Value", "Test Date"]
        assert value_range["values"][1] == ["Alice", "100", "2024-01-01"]
        assert value_range["values"][2] == ["Bob", "200", "2024-01-02"]

    @pytest.mark.asyncio
    async def test_e2e_get_values_multiple_ranges(self, setup_mcp_instance, test_spreadsheet_id):
        """Test getting values from multiple ranges with real API."""
        instance = setup_mcp_instance
        
        # Prepare test data in different areas
        # First range
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!A1:B2",
            valueInputOption="USER_ENTERED",
            body={"values": [["Header1", "Header2"], ["Data1", "Data2"]]}
        ).execute()
        
        # Second range
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!E5:F7",
            valueInputOption="USER_ENTERED",
            body={"values": [["Col1", "Col2"], ["Val1", "Val2"], ["Val3", "Val4"]]}
        ).execute()
        
        # Third range (with formulas)
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!H1:H3",
            valueInputOption="USER_ENTERED",
            body={"values": [["=1+1"], ["=2*3"], ["=SUM(1,2,3)"]]}
        ).execute()

        # Test get_values with multiple ranges
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": ["Sheet1!A1:B2", "Sheet1!E5:F7", "Sheet1!H1:H3"]
        })

        # Verify result
        data = json.loads(result)
        assert len(data["valueRanges"]) == 3
        
        # Check first range
        assert data["valueRanges"][0]["values"] == [["Header1", "Header2"], ["Data1", "Data2"]]
        
        # Check second range
        assert len(data["valueRanges"][1]["values"]) == 3
        assert data["valueRanges"][1]["values"][0] == ["Col1", "Col2"]
        
        # Check third range (formulas should be calculated)
        assert data["valueRanges"][2]["values"] == [["2"], ["6"], ["6"]]

    @pytest.mark.asyncio
    async def test_e2e_get_values_with_render_options(self, setup_mcp_instance, test_spreadsheet_id):
        """Test get_values with different render options."""
        instance = setup_mcp_instance
        
        # Prepare test data with formulas
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!J1:J3",
            valueInputOption="USER_ENTERED",
            body={"values": [["=10+5"], ["=A1"], ["=SUM(15,20)"]]}
        ).execute()

        # Test with FORMULA render option
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": "Sheet1!J1:J3",
            "value_render_option": "FORMULA"
        })

        # Verify formulas are returned
        data = json.loads(result)
        values = data["valueRanges"][0]["values"]
        assert values[0][0] == "=10+5"
        assert values[1][0] == "=A1"
        assert values[2][0] == "=SUM(15,20)"

        # Test with UNFORMATTED_VALUE render option
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": "Sheet1!J1:J3",
            "value_render_option": "UNFORMATTED_VALUE"
        })

        # Verify raw values are returned
        data = json.loads(result)
        values = data["valueRanges"][0]["values"]
        assert values[0][0] == 15  # Calculated value
        # values[1][0] depends on what's in A1
        assert values[2][0] == 35  # Calculated value

    @pytest.mark.asyncio
    async def test_e2e_get_values_empty_ranges(self, setup_mcp_instance, test_spreadsheet_id):
        """Test getting values from empty ranges."""
        instance = setup_mcp_instance
        
        # Clear a range to ensure it's empty
        await instance.sheets_service.values().clear(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!Z50:AA55"
        ).execute()

        # Test get_values with empty range
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": "Sheet1!Z50:AA55"
        })

        # Verify empty range handling
        data = json.loads(result)
        assert len(data["valueRanges"]) == 1
        assert "Sheet1!Z50:AA55" in data["valueRanges"][0]["range"]
        # Empty ranges don't have a "values" key
        assert "values" not in data["valueRanges"][0]

    @pytest.mark.asyncio
    async def test_e2e_get_values_mixed_data_types(self, setup_mcp_instance, test_spreadsheet_id):
        """Test getting values with various data types."""
        instance = setup_mcp_instance
        
        # Prepare diverse data types
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range="Sheet1!L1:O4",
            valueInputOption="USER_ENTERED",
            body={
                "values": [
                    ["String", "123", "45.67", "TRUE"],
                    ["Multi word", "0", "-89.01", "FALSE"],
                    ["", "-456", "0.0", ""],
                    ["Special!@#", "9999999", "1.23e-4", "Yes"]
                ]
            }
        ).execute()

        # Test get_values
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": "Sheet1!L1:O4"
        })

        # Verify data types are preserved
        data = json.loads(result)
        values = data["valueRanges"][0]["values"]
        
        # All values should be strings in FORMATTED_VALUE mode
        assert values[0] == ["String", "123", "45.67", "TRUE"]
        assert values[1] == ["Multi word", "0", "-89.01", "FALSE"]
        assert values[2] == ["", "-456", "0", ""]  # Note: 0.0 might be formatted as "0"
        assert values[3][0] == "Special!@#"
        assert values[3][1] == "9999999"
        # Scientific notation might be formatted differently

    @pytest.mark.asyncio
    async def test_e2e_get_values_large_batch(self, setup_mcp_instance, test_spreadsheet_id):
        """Test getting values from many ranges in a single batch."""
        instance = setup_mcp_instance
        
        # Prepare data in multiple locations
        ranges_to_populate = [
            ("Sheet1!A10:A12", [["R1"], ["R2"], ["R3"]]),
            ("Sheet1!C10:C12", [["R4"], ["R5"], ["R6"]]),
            ("Sheet1!E10:E12", [["R7"], ["R8"], ["R9"]]),
            ("Sheet1!G10:G12", [["R10"], ["R11"], ["R12"]]),
            ("Sheet1!I10:I12", [["R13"], ["R14"], ["R15"]])
        ]
        
        for range_addr, values in ranges_to_populate:
            await instance.sheets_service.values().update(
                spreadsheetId=test_spreadsheet_id,
                range=range_addr,
                valueInputOption="USER_ENTERED",
                body={"values": values}
            ).execute()

        # Test batch get
        ranges = [r[0] for r in ranges_to_populate]
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": ranges
        })

        # Verify all ranges were retrieved
        data = json.loads(result)
        assert len(data["valueRanges"]) == 5
        
        # Verify each range has correct data
        for i, value_range in enumerate(data["valueRanges"]):
            expected_values = ranges_to_populate[i][1]
            assert value_range["values"] == expected_values

    @pytest.mark.asyncio
    async def test_e2e_get_values_error_handling(self, setup_mcp_instance, test_spreadsheet_id):
        """Test error handling with invalid ranges."""
        # Test with invalid range syntax
        with pytest.raises(Exception) as exc_info:
            await GoogleSheetsMCP.get_values({
                "file_id": test_spreadsheet_id,
                "ranges": "InvalidRangeFormat"
            })
        
        # Should get an API error about invalid range
        assert "Invalid" in str(exc_info.value) or "invalid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_e2e_get_values_cross_sheet(self, setup_mcp_instance, test_spreadsheet_id):
        """Test getting values across multiple sheets if available."""
        instance = setup_mcp_instance
        
        # First, check if we have multiple sheets
        spreadsheet = await instance.sheets_service.get(
            spreadsheetId=test_spreadsheet_id
        ).execute()
        
        sheet_names = [sheet["properties"]["title"] for sheet in spreadsheet["sheets"]]
        
        if len(sheet_names) < 2:
            pytest.skip("Test spreadsheet needs at least 2 sheets for this test")
        
        # Use first two sheets
        sheet1 = sheet_names[0]
        sheet2 = sheet_names[1]
        
        # Populate data in both sheets
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range=f"{sheet1}!A1:A2",
            valueInputOption="USER_ENTERED",
            body={"values": [["Sheet1 Data"], ["More S1 Data"]]}
        ).execute()
        
        await instance.sheets_service.values().update(
            spreadsheetId=test_spreadsheet_id,
            range=f"{sheet2}!A1:A2",
            valueInputOption="USER_ENTERED",
            body={"values": [["Sheet2 Data"], ["More S2 Data"]]}
        ).execute()

        # Test cross-sheet batch get
        result = await GoogleSheetsMCP.get_values({
            "file_id": test_spreadsheet_id,
            "ranges": [f"{sheet1}!A1:A2", f"{sheet2}!A1:A2"]
        })

        # Verify data from both sheets
        data = json.loads(result)
        assert len(data["valueRanges"]) == 2
        assert data["valueRanges"][0]["values"] == [["Sheet1 Data"], ["More S1 Data"]]
        assert data["valueRanges"][1]["values"] == [["Sheet2 Data"], ["More S2 Data"]]
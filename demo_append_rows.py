#!/usr/bin/env python3
"""
Demonstration script for the append_rows functionality.

This script shows how to use the new append_rows MCP tool to add data
to the end of existing Google Sheets.
"""

import asyncio
import json
from google_sheets import GoogleSheetsMCP, mcp


async def demo_append_rows():
    """Demonstrate append_rows functionality."""
    print("Google Sheets MCP - append_rows Demonstration")
    print("=" * 50)
    
    # Initialize the MCP instance
    instance = GoogleSheetsMCP()
    mcp._instance = instance
    
    try:
        # Note: This would require actual Google API credentials
        print("Creating a test spreadsheet...")
        
        # Example 1: Create a new sheet
        create_result = await GoogleSheetsMCP.create_sheet("Append Rows Demo")
        sheet_data = json.loads(create_result)
        sheet_id = sheet_data["spreadsheetId"]
        print(f"Created sheet: {sheet_id}")
        
        # Example 2: Append header row
        print("\n1. Appending header row...")
        headers = [["Name", "Age", "City", "Score"]]
        result = await GoogleSheetsMCP.append_rows(
            file_id=sheet_id,
            range="Sheet1",
            values=headers
        )
        print(f"Result: {json.loads(result)}")
        
        # Example 3: Append multiple data rows
        print("\n2. Appending multiple data rows...")
        data_rows = [
            ["Alice", 30, "New York", 95.5],
            ["Bob", 25, "San Francisco", 87.2],
            ["Charlie", 35, "Chicago", 92.8]
        ]
        result = await GoogleSheetsMCP.append_rows(
            file_id=sheet_id,
            range="Sheet1",
            values=data_rows
        )
        print(f"Result: {json.loads(result)}")
        
        # Example 4: Append with formulas
        print("\n3. Appending formulas...")
        formula_rows = [
            ["", "", "Average:", "=AVERAGE(D2:D4)"],
            ["", "", "Max:", "=MAX(D2:D4)"]
        ]
        result = await GoogleSheetsMCP.append_rows(
            file_id=sheet_id,
            range="Sheet1",
            values=formula_rows,
            value_input_option="USER_ENTERED"
        )
        print(f"Result: {json.loads(result)}")
        
        # Example 5: Append to specific columns
        print("\n4. Appending to specific column range...")
        column_data = [["David", 28]]
        result = await GoogleSheetsMCP.append_rows(
            file_id=sheet_id,
            range="Sheet1!A:B",  # Only columns A and B
            values=column_data
        )
        print(f"Result: {json.loads(result)}")
        
        # Example 6: Read back the data to verify
        print("\n5. Reading back all data...")
        read_result = await GoogleSheetsMCP.read_range(
            file_id=sheet_id,
            range="Sheet1!A1:D10"
        )
        all_data = json.loads(read_result)
        print("Final sheet contents:")
        for i, row in enumerate(all_data.get("values", []), 1):
            print(f"  Row {i}: {row}")
            
        print(f"\nDemo complete! Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: This demo requires valid Google API credentials.")
        print("To run with real API access:")
        print("1. Set up Google Sheets API credentials")
        print("2. Run: python google_sheets.py --credentials path/to/credentials.json")
        print("3. Then run this demo script")


def show_usage_examples():
    """Show code examples of how to use append_rows."""
    print("\nUsage Examples:")
    print("=" * 30)
    
    examples = [
        {
            "title": "Basic append",
            "code": '''await GoogleSheetsMCP.append_rows(
    file_id="your-sheet-id",
    range="Sheet1",
    values=[["Row1Col1", "Row1Col2"], ["Row2Col1", "Row2Col2"]]
)'''
        },
        {
            "title": "Append with formulas",
            "code": '''await GoogleSheetsMCP.append_rows(
    file_id="your-sheet-id",
    range="Sheet1",
    values=[["Total", "=SUM(A:A)"]],
    value_input_option="USER_ENTERED"
)'''
        },
        {
            "title": "Append to specific columns",
            "code": '''await GoogleSheetsMCP.append_rows(
    file_id="your-sheet-id",
    range="Sheet1!C:E",
    values=[["Col C", "Col D", "Col E"]]
)'''
        },
        {
            "title": "Raw data (no formula parsing)",
            "code": '''await GoogleSheetsMCP.append_rows(
    file_id="your-sheet-id",
    range="Sheet1",
    values=[["=SUM(A1:A10)", "Raw formula text"]],
    value_input_option="RAW"
)'''
        },
        {
            "title": "Insert rows (shift existing data down)",
            "code": '''await GoogleSheetsMCP.append_rows(
    file_id="your-sheet-id",
    range="Sheet1!A2",
    values=[["Inserted row"]],
    insert_data_option="INSERT_ROWS"
)'''
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print(example['code'])


if __name__ == "__main__":
    print("Google Sheets MCP Server - append_rows Implementation")
    print("=" * 60)
    
    print("\nFeatures implemented:")
    print("• Append single or multiple rows to sheets")
    print("• Support for different data types (strings, numbers, booleans, formulas)")
    print("• Value input options (RAW, USER_ENTERED)")
    print("• Insert data options (OVERWRITE, INSERT_ROWS)")
    print("• Append to specific column ranges")
    print("• Comprehensive error handling and validation")
    print("• Full test coverage with unit and E2E tests")
    
    show_usage_examples()
    
    print("\n" + "=" * 60)
    print("Implementation Details:")
    print("• Follows MCP static handler pattern")
    print("• Uses Google Sheets append API for efficiency")
    print("• Handles data type conversion automatically")
    print("• Returns detailed update information")
    print("• Comprehensive input validation")
    
    print("\nTo run the live demo (requires credentials):")
    print("python demo_append_rows.py --demo")
    
    if "--demo" in __import__("sys").argv:
        asyncio.run(demo_append_rows())
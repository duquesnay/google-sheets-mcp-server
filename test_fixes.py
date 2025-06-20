#!/usr/bin/env python3
"""
Quick test to verify the fixes work
"""
import asyncio
import json
from unittest.mock import Mock, patch
from google_sheets import GoogleSheetsMCP, mcp

async def test_get_sheet_properties_fix():
    """Test that get_sheet_properties returns string, not coroutine"""
    # Setup mock instance
    mock_instance = Mock()
    mock_service = Mock()
    mock_spreadsheets = Mock()
    mock_get = Mock()
    
    # Setup mock chain
    mock_instance.sheets_service = mock_service
    mock_service.spreadsheets.return_value = mock_spreadsheets
    mock_spreadsheets.get.return_value = mock_get
    mock_get.execute.return_value = {
        'sheets': [{'properties': {'title': 'Sheet1', 'sheetId': 0}}]
    }
    
    # Set the global instance
    mcp._instance = mock_instance
    
    # Call the static method directly
    result = await GoogleSheetsMCP.get_sheet_properties("test_sheet_id")
    
    # Verify it returns a JSON string
    assert isinstance(result, str), f"Expected string, got {type(result)}"
    
    # Verify it's valid JSON
    data = json.loads(result)
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) == 1
    assert data[0]['properties']['title'] == 'Sheet1'
    
    print("✅ get_sheet_properties now returns JSON string correctly")

async def test_write_formula_fix():
    """Test that write_formula uses correct API format"""
    # Setup mock instance
    mock_instance = Mock()
    mock_service = Mock()
    mock_spreadsheets = Mock()
    mock_values = Mock()
    mock_update = Mock()
    
    # Setup mock chain
    mock_instance.sheets_service = mock_service
    mock_service.spreadsheets.return_value = mock_spreadsheets
    mock_spreadsheets.values.return_value = mock_values
    mock_values.update.return_value = mock_update
    mock_update.execute.return_value = {}
    
    # Set the global instance
    mcp._instance = mock_instance
    
    # Call the static method directly
    result = await GoogleSheetsMCP.write_formula("test_sheet_id", "A1", "=SUM(B1:B10)")
    
    # Verify it returns a JSON string
    assert isinstance(result, str), f"Expected string, got {type(result)}"
    
    # Verify the API was called with correct format
    mock_values.update.assert_called_once()
    call_args = mock_values.update.call_args
    assert call_args[1]['body']['values'] == [["=SUM(B1:B10)"]]  # Simple string, not complex object
    
    print("✅ write_formula now uses correct API format")

async def main():
    """Run all tests"""
    print("Testing fixes...")
    
    try:
        await test_get_sheet_properties_fix()
        await test_write_formula_fix()
        print("\n🎉 All fixes working correctly!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
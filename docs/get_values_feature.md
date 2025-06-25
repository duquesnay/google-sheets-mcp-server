# Get Values Feature Documentation

## Overview

The `get_values` tool provides efficient batch reading of multiple ranges from Google Sheets in a single API call. This is more efficient than making multiple individual `read_range` calls.

## Function Signature

```python
async def get_values(
    file_id: str,
    ranges: Union[str, List[str]],
    value_render_option: Optional[str] = None,
    date_time_render_option: Optional[str] = None
) -> str
```

## Parameters

- **file_id** (required): The ID of the Google Sheet
- **ranges** (required): Single range string or list of ranges in A1 notation
  - Single range example: `"Sheet1!A1:B10"`
  - Multiple ranges example: `["Sheet1!A1:B10", "Sheet2!C1:D5", "Sheet1!E1:F3"]`
- **value_render_option** (optional): How values should be represented
  - `"FORMATTED_VALUE"` (default): Values as they appear in the UI
  - `"UNFORMATTED_VALUE"`: Raw values without formatting
  - `"FORMULA"`: Formula strings instead of calculated values
- **date_time_render_option** (optional): How dates should be represented
  - `"FORMATTED_STRING"` (default): Formatted date/time strings
  - `"SERIAL_NUMBER"`: Date/time as serial numbers

## Return Value

Returns a JSON string containing:
- `spreadsheetId`: The ID of the spreadsheet
- `valueRanges`: Array of range data, each containing:
  - `range`: The range in A1 notation (may be adjusted by the API)
  - `values`: 2D array of cell values (omitted if range is empty)

## Usage Examples

### Single Range
```python
result = await GoogleSheetsMCP.get_values(
    file_id="your-sheet-id",
    ranges="Sheet1!A1:C10"
)
```

### Multiple Ranges
```python
result = await GoogleSheetsMCP.get_values(
    file_id="your-sheet-id",
    ranges=["Sheet1!A1:C10", "Sheet2!D1:F5", "Summary!A1:B3"]
)
```

### With Custom Render Options
```python
result = await GoogleSheetsMCP.get_values(
    file_id="your-sheet-id",
    ranges=["Sheet1!A1:B10"],
    value_render_option="FORMULA",
    date_time_render_option="SERIAL_NUMBER"
)
```

## Response Example

```json
{
  "spreadsheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
  "valueRanges": [
    {
      "range": "Sheet1!A1:C3",
      "values": [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "San Francisco"]
      ]
    },
    {
      "range": "Sheet2!A1:B2",
      "values": [
        ["Product", "Price"],
        ["Apple", "$1.99"]
      ]
    },
    {
      "range": "Sheet3!Z100:AA101"
      // No "values" key when range is empty
    }
  ]
}
```

## Benefits Over read_range

1. **Efficiency**: Single API call for multiple ranges reduces latency
2. **Batch Operations**: Ideal for dashboards or reports needing data from multiple areas
3. **Atomic Reading**: All ranges are read at the same point in time
4. **Same Options**: Supports all the same render options as read_range

## Error Handling

The tool will raise exceptions for:
- Invalid sheet ID (404 error)
- Invalid range format (400 error)
- Authentication/permission issues
- Network or API errors

Partial failures (e.g., one invalid range among many) will cause the entire operation to fail, ensuring consistency.

## Implementation Details

- Uses Google Sheets API v4 `batchGet` method
- Automatically converts single range string to list for API compatibility
- Returns the full API response as JSON for maximum flexibility
- Empty ranges are included in results but without a "values" key
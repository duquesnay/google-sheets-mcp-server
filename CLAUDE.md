   git # CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Google Sheets MCP (Model Context Protocol) server that provides tools for interacting with Google Sheets through the MCP protocol. The server uses FastMCP framework and integrates with Google Sheets API.

## Development Commands

### Running the Server
```bash
# With service account credentials
python google_sheets.py --credentials /path/to/service-account-key.json

# With OAuth2 (interactive browser auth)
python google_sheets.py --oauth

# With verbose logging
python google_sheets.py --credentials key.json --verbose
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_google_sheets.py -v

# Run with coverage
pytest --cov=google_sheets --cov-report=html
```

### Type Checking
```bash
# Type check (if mypy is installed)
mypy google_sheets.py --strict
```

## Architecture Overview

### Core Design Pattern
The server follows a specific pattern required by FastMCP:

1. **Global Instance Pattern**: A singleton `GoogleSheetsMCP` instance is stored in `mcp._instance`
2. **Static Method Handlers**: All MCP tools are static methods decorated with `@mcp.tool()`
3. **Instance Access**: Static methods retrieve the instance via `mcp._instance` and call instance methods

```python
@mcp.tool()
async def tool_name(args) -> str:
    """MCP tool handler - must be static."""
    instance = mcp._instance
    return await instance.method_name(args)  # Delegates to instance
```

### Key Components

1. **google_sheets.py**: Main server file
   - `GoogleSheetsMCP` class: Core functionality
   - Static MCP tool handlers
   - Google API integration
   - Error handling and retry logic

2. **Authentication**: Supports two modes
   - Service Account (via JSON key file)
   - OAuth2 (browser-based flow)

3. **MCP Tools**:
   - `create_sheet`: Creates new spreadsheets
   - `get_sheet_properties`: Retrieves sheet metadata
   - `write_formula`: Writes formulas to cells
   - `format_range`: Applies formatting
   - `add_sheet`: Adds new sheets to spreadsheets
   - `delete_sheet`: Removes sheets

### Critical Integration Points

1. **Async/Await Handling**: All MCP handlers must properly await async methods
2. **JSON Returns**: All tools must return JSON strings, not Python objects
3. **Error Handling**: Custom exceptions with proper MCP error responses
4. **API Field Names**: Google Sheets API uses `fields` (not `field`) for partial responses

## Testing Strategy (Lessons Learned)

### The Four-Layer Testing Approach
1. **Unit Tests**: Test individual methods with mocks
2. **Integration Tests**: Test MCP handlers → methods → API calls
3. **Protocol Tests**: Test actual MCP communication via stdio
4. **End-to-End Tests**: Test full client → server → Google Sheets

### Critical Testing Pattern
```python
# Always test the actual MCP handler, not just internal methods
async def test_mcp_handler():
    result = await tool_name({"arg": "value"})
    assert isinstance(result, str)  # Must be string
    data = json.loads(result)  # Must be valid JSON
```

### Pre-Deployment Checklist
1. Run `pytest` - ensure all tests pass
2. Test MCP protocol layer manually
3. Verify JSON serialization of all returns
4. Check async/await at all levels
5. Test with actual Google Sheets API

## Common Pitfalls to Avoid

1. **"It Starts ≠ It Works"**: Server initialization doesn't mean tools function correctly
2. **Coroutine Returns**: Ensure all async methods are awaited
3. **Type Mismatches**: All MCP tools must return strings, not objects
4. **API Structure**: Google Sheets API has specific payload formats - verify against docs
5. **Testing Wrong Layer**: Test MCP handlers, not just internal methods

## Google Sheets API Specifics

### Cell/Range References
- A1 notation: "Sheet1!A1:B10"
- R1C1 notation also supported
- Named ranges can be used

### Common API Patterns
```python
# Batch update pattern
batch_update_request = {
    "requests": [
        {
            "updateCells": {
                "range": {...},
                "fields": "userEnteredValue"
            }
        }
    ]
}

# Value update pattern
values = {
    "values": [[val1, val2], [val3, val4]],
    "range": "A1:B2"
}
```

### Authentication Flow
1. Service Account: Requires JSON key with Sheets API access
2. OAuth2: Opens browser for user consent, stores token locally

## Development Workflow

1. **Make Changes**: Edit code with proper type hints
2. **Test Locally**: Run pytest before any integration
3. **Protocol Test**: Test actual MCP communication
4. **Type Check**: Run mypy if available
5. **Integration Test**: Test with Claude Desktop or MCP client

## Debugging Tips

1. Use `--verbose` flag for detailed logging
2. Check `~/.mcp/logs/` for server logs
3. Test tools individually before full integration
4. Verify Google Sheets API credentials and permissions
5. Use `test_mcp_protocol.py` for protocol-level debugging

## Project Learnings

### 2025-01-06 - Implementation of Missing Google Sheets MCP Features

**Technical:**
- **Google Sheets API Has Subtle Inconsistencies**: Empty ranges don't have a "values" key in the response (requires defensive coding). `batchGet` returns `valueRanges` (plural) while single `get` returns `values`. Boolean values need explicit string conversion ("TRUE"/"FALSE") for proper display.
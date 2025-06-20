# Proper TDD Strategy for MCP Servers

## 1. Unit Test Each Function
```python
# test_google_sheets_functions.py
async def test_get_sheet_properties():
    """Test that get_sheet_properties returns JSON, not coroutine"""
    result = await GoogleSheetsMCP.get_sheet_properties(test_sheet_id)
    assert isinstance(result, str)  # Should be JSON string
    data = json.loads(result)
    assert 'sheets' in data

async def test_format_range():
    """Test format_range API payload structure"""
    # Mock the API call to catch malformed requests
    with mock.patch('googleapiclient.discovery.build') as mock_build:
        await GoogleSheetsMCP.format_range(sheet_id, "A1:B2", {"bold": True})
        # Verify the API was called with correct structure
        assert_api_payload_valid(mock_build.call_args)
```

## 2. Integration Test with MCP Protocol
```python
# test_mcp_integration.py
async def test_mcp_tool_invocation():
    """Test actual MCP protocol communication"""
    # Start server in test mode
    server = start_test_mcp_server()
    
    # Simulate MCP client
    client = MCPTestClient(server)
    
    # Test each tool
    response = await client.call_tool("get_sheet_properties", {
        "file_id": "test_sheet_id"
    })
    
    # Validate response structure
    assert response['result'] is not None
    assert not response.get('error')
```

## 3. API Contract Tests
```python
# test_google_api_contracts.py
def test_format_request_structure():
    """Validate our requests match Google's API spec"""
    request = build_format_request({"bold": True})
    
    # Check against Google Sheets API v4 spec
    assert 'requests' in request
    assert 'repeatCell' in request['requests'][0]
    assert 'fields' in request['requests'][0]['repeatCell']
    # NOT 'field' - this was the bug!
```

## 4. Type Safety
```python
from typing import TypedDict, Awaitable

class FormatRequest(TypedDict):
    requests: list[dict]

async def format_range(
    self, 
    file_id: str, 
    range: str, 
    format: dict
) -> str:  # NOT Awaitable[str] if we're returning directly
```

## 5. Test Harness for MCP Servers
```bash
#!/bin/bash
# test_mcp_server.sh

# Start server with test config
export TEST_MODE=1
python google_sheets.py --service-account test-key.json &
SERVER_PID=$!

# Run MCP protocol tests
python -m pytest tests/mcp_protocol_tests.py

# Test actual tool calls
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_sheet_properties","arguments":{"file_id":"test"}},"id":1}' | \
  python google_sheets.py --service-account test-key.json | \
  jq -e '.result != null'

kill $SERVER_PID
```

## 6. Pre-commit Validation
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: test-mcp-functions
        name: Test MCP Functions
        entry: python -m pytest tests/test_functions.py
        language: system
        always_run: true
```

## Key Lessons

1. **Never trust "it starts"** - Test actual functionality
2. **Mock external APIs** - Don't rely on live Google Sheets for testing
3. **Test the protocol** - MCP has specific requirements
4. **Validate contracts** - API specs matter (fields vs field)
5. **Automate everything** - Manual testing misses async bugs

## Red Flags We Missed

- 🚩 No await in async functions = returns coroutine
- 🚩 No JSON serialization = returns Python objects
- 🚩 No API contract validation = wrong field names
- 🚩 No response format testing = protocol violations
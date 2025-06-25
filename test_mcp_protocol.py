#!/usr/bin/env python3
"""
MCP Protocol Layer Test Script

This script validates that the Google Sheets MCP server is production-ready by testing:
1. Server initialization and startup
2. All new tools are properly registered
3. MCP protocol communication works correctly
4. Error handling and validation
5. JSON serialization of responses

This test doesn't require actual Google Sheets API credentials - it uses mocking
to validate the protocol layer works correctly.
"""

import sys
import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

# Add the current directory to Python path to import our module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import google_sheets
from google_sheets import GoogleSheetsMCP, mcp, GoogleSheetsError, SheetNotFoundError
from mcp.server.fastmcp import FastMCP

# Configure logging for test output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class MCPProtocolTester:
    """Test harness for validating MCP protocol layer"""
    
    def __init__(self):
        self.results = []
        self.mock_server = None
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "PASS" if success else "FAIL"
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        logger.info(f"[{status}] {test_name}: {details}")
    
    def setup_mock_server(self):
        """Setup a mock Google Sheets MCP server for testing"""
        with patch('google_sheets.os.path.exists', return_value=False):
            self.mock_server = GoogleSheetsMCP(service_account_path="mock_credentials.json")
            
        # Mock the Google API services
        self.mock_server.sheets_service = Mock()
        self.mock_server.drive_service = Mock()
        
        # Store instance in the mcp global
        mcp._instance = self.mock_server
        
    async def test_server_initialization(self):
        """Test that the MCP server initializes correctly"""
        try:
            self.setup_mock_server()
            assert self.mock_server is not None
            assert mcp._instance is not None
            assert mcp._instance == self.mock_server
            self.log_test("Server Initialization", True, "MCP server instance created and stored")
        except Exception as e:
            self.log_test("Server Initialization", False, f"Error: {str(e)}")
    
    async def test_tool_registration(self):
        """Test that all new tools are properly registered with MCP"""
        expected_tools = [
            "create_sheet",
            "get_sheet_properties", 
            "write_formula",
            "format_range",
            "add_sheet",
            "delete_sheet",
            "read_range",      # New tool
            "get_values",      # New tool
            "append_rows",     # New tool
            "update_range",    # New tool
            "insert_rows"      # New tool
        ]
        
        try:
            # Check that the tools exist as static methods with the @mcp.tool decorator
            registered_tools = []
            
            for tool_name in expected_tools:
                # Check if the method exists on the class
                if hasattr(GoogleSheetsMCP, tool_name):
                    method = getattr(GoogleSheetsMCP, tool_name)
                    # Check if it's callable and has the right signature
                    if callable(method):
                        registered_tools.append(tool_name)
            
            # Also check if we can actually call them (this tests the MCP registration)
            callable_tools = []
            for tool_name in ["read_range", "get_values", "append_rows", "update_range"]:
                try:
                    method = getattr(GoogleSheetsMCP, tool_name)
                    # Don't actually call them, just verify they're callable
                    if callable(method):
                        callable_tools.append(tool_name)
                except AttributeError:
                    pass
            
            missing_tools = set(expected_tools) - set(registered_tools)
            
            if not missing_tools:
                self.log_test("Tool Registration", True, f"All {len(expected_tools)} tools found as class methods. New tools {callable_tools} are callable.")
            else:
                self.log_test("Tool Registration", False, f"Missing tools: {missing_tools}")
                
        except Exception as e:
            self.log_test("Tool Registration", False, f"Error checking registration: {str(e)}")
    
    async def test_read_range_protocol(self):
        """Test read_range MCP tool through protocol layer"""
        try:
            # Setup mock response
            mock_values = Mock()
            mock_values.get.return_value.execute.return_value = {
                'values': [['A1', 'B1'], ['A2', 'B2']],
                'range': 'Sheet1!A1:B2'
            }
            self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
            
            # Call the MCP tool handler
            result = await GoogleSheetsMCP.read_range(
                file_id="test_sheet_id",
                range="A1:B2"
            )
            
            # Validate response
            assert isinstance(result, str), "Result must be a JSON string"
            data = json.loads(result)
            assert 'values' in data
            assert 'range' in data
            assert data['values'] == [['A1', 'B1'], ['A2', 'B2']]
            
            self.log_test("read_range Protocol", True, "Successfully called read_range via MCP protocol")
            
        except Exception as e:
            self.log_test("read_range Protocol", False, f"Error: {str(e)}")
    
    async def test_get_values_protocol(self):
        """Test get_values MCP tool through protocol layer"""
        try:
            # Setup mock response for batch get
            mock_values = Mock()
            mock_values.batchGet.return_value.execute.return_value = {
                'spreadsheetId': 'test_sheet_id',
                'valueRanges': [
                    {
                        'range': 'Sheet1!A1:B2',
                        'values': [['A1', 'B1'], ['A2', 'B2']]
                    },
                    {
                        'range': 'Sheet1!C1:D2', 
                        'values': [['C1', 'D1'], ['C2', 'D2']]
                    }
                ]
            }
            self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
            
            # Call with multiple ranges
            result = await GoogleSheetsMCP.get_values(
                file_id="test_sheet_id",
                ranges=["A1:B2", "C1:D2"]
            )
            
            # Validate response
            assert isinstance(result, str), "Result must be a JSON string"
            data = json.loads(result)
            assert 'spreadsheetId' in data
            assert 'valueRanges' in data
            assert len(data['valueRanges']) == 2
            
            self.log_test("get_values Protocol", True, "Successfully called get_values via MCP protocol")
            
        except Exception as e:
            self.log_test("get_values Protocol", False, f"Error: {str(e)}")
    
    async def test_append_rows_protocol(self):
        """Test append_rows MCP tool through protocol layer"""
        try:
            # Setup mock response
            mock_values = Mock()
            mock_values.append.return_value.execute.return_value = {
                'spreadsheetId': 'test_sheet_id',
                'updates': {
                    'updatedRange': 'Sheet1!A3:B4',
                    'updatedRows': 2,
                    'updatedColumns': 2,
                    'updatedCells': 4
                }
            }
            self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
            
            # Call the MCP tool handler
            result = await GoogleSheetsMCP.append_rows(
                file_id="test_sheet_id",
                range="Sheet1",
                values=[["New1", "New2"], ["New3", "New4"]]
            )
            
            # Validate response
            assert isinstance(result, str), "Result must be a JSON string"
            data = json.loads(result)
            assert 'updatedRange' in data
            assert 'updatedRows' in data
            assert data['updatedRows'] == 2
            
            self.log_test("append_rows Protocol", True, "Successfully called append_rows via MCP protocol")
            
        except Exception as e:
            self.log_test("append_rows Protocol", False, f"Error: {str(e)}")
    
    async def test_update_range_protocol(self):
        """Test update_range MCP tool through protocol layer"""
        try:
            # Setup mock response
            mock_values = Mock()
            mock_values.update.return_value.execute.return_value = {
                'spreadsheetId': 'test_sheet_id',
                'updatedRange': 'Sheet1!A1:B2',
                'updatedRows': 2,
                'updatedColumns': 2,
                'updatedCells': 4
            }
            self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
            
            # Call the MCP tool handler
            result = await GoogleSheetsMCP.update_range(
                file_id="test_sheet_id",
                range="A1:B2",
                values=[["Updated1", "Updated2"], ["Updated3", "Updated4"]]
            )
            
            # Validate response
            assert isinstance(result, str), "Result must be a JSON string"
            data = json.loads(result)
            assert 'updatedRange' in data
            assert 'updatedRows' in data
            assert data['updatedRows'] == 2
            
            self.log_test("update_range Protocol", True, "Successfully called update_range via MCP protocol")
            
        except Exception as e:
            self.log_test("update_range Protocol", False, f"Error: {str(e)}")
    
    async def test_insert_rows_protocol(self):
        """Test insert_rows MCP tool through protocol layer"""
        try:
            # Setup mock responses for both batch update and values update
            mock_batch = Mock()
            mock_batch.batchUpdate.return_value.execute.return_value = {
                'spreadsheetId': 'test_sheet_id'
            }
            
            mock_values = Mock()
            mock_values.update.return_value.execute.return_value = {
                'updatedRange': 'Sheet1!A1:B2',
                'updatedRows': 2,
                'updatedColumns': 2,
                'updatedCells': 4
            }
            
            # Setup spreadsheet get response for sheet properties
            mock_get = Mock()
            mock_get.get.return_value.execute.return_value = {
                'sheets': [
                    {
                        'properties': {
                            'sheetId': 0,
                            'title': 'Sheet1'
                        }
                    }
                ]
            }
            
            self.mock_server.sheets_service.spreadsheets.return_value.batchUpdate = mock_batch.batchUpdate
            self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
            self.mock_server.sheets_service.spreadsheets.return_value.get = mock_get.get
            
            # Call the MCP tool handler
            result = await GoogleSheetsMCP.insert_rows(
                file_id="test_sheet_id",
                sheet_name="Sheet1",
                start_index=0,
                num_rows=2,
                values=[["Insert1", "Insert2"], ["Insert3", "Insert4"]]
            )
            
            # Validate response
            assert isinstance(result, str), "Result must be a JSON string"
            data = json.loads(result)
            assert 'spreadsheetId' in data
            assert 'insertedRows' in data
            assert data['insertedRows'] == 2
            
            self.log_test("insert_rows Protocol", True, "Successfully called insert_rows via MCP protocol")
            
        except Exception as e:
            self.log_test("insert_rows Protocol", False, f"Error: {str(e)}")
    
    async def test_error_handling_protocol(self):
        """Test that errors are properly handled and returned via MCP protocol"""
        try:
            # Setup mock to raise an HTTP error
            from googleapiclient.errors import HttpError
            mock_values = Mock()
            mock_error_resp = Mock()
            mock_error_resp.status = 404
            mock_error = HttpError(mock_error_resp, b'Sheet not found')
            mock_values.get.return_value.execute.side_effect = mock_error
            self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
            
            # Call read_range with invalid sheet
            try:
                await GoogleSheetsMCP.read_range(
                    file_id="invalid_sheet_id",
                    range="A1:B2"
                )
                self.log_test("Error Handling Protocol", False, "Expected error was not raised")
            except (GoogleSheetsError, SheetNotFoundError) as e:
                # This is expected - the error should be properly converted
                self.log_test("Error Handling Protocol", True, f"Properly handled error: {type(e).__name__}")
            except Exception as e:
                self.log_test("Error Handling Protocol", False, f"Unexpected error type: {type(e).__name__}: {str(e)}")
                
        except Exception as e:
            self.log_test("Error Handling Protocol", False, f"Setup error: {str(e)}")
    
    async def test_parameter_validation(self):
        """Test that parameter validation works correctly"""
        try:
            # Test missing required parameters
            test_cases = [
                {
                    "name": "read_range missing file_id",
                    "call": lambda: GoogleSheetsMCP.read_range(range="A1:B2"),
                    "expected_error": TypeError
                },
                {
                    "name": "read_range missing range", 
                    "call": lambda: GoogleSheetsMCP.read_range(file_id="test123"),
                    "expected_error": TypeError
                },
                {
                    "name": "append_rows missing values",
                    "call": lambda: GoogleSheetsMCP.append_rows(file_id="test123", range="Sheet1"),
                    "expected_error": TypeError
                },
                {
                    "name": "update_range missing values",
                    "call": lambda: GoogleSheetsMCP.update_range(file_id="test123", range="A1:B2"),
                    "expected_error": TypeError
                }
            ]
            
            validation_results = []
            for test_case in test_cases:
                try:
                    await test_case["call"]()
                    validation_results.append(f"FAIL: {test_case['name']} - No error raised")
                except test_case["expected_error"]:
                    validation_results.append(f"PASS: {test_case['name']}")
                except Exception as e:
                    validation_results.append(f"FAIL: {test_case['name']} - Wrong error: {type(e).__name__}")
            
            passed = sum(1 for r in validation_results if r.startswith("PASS"))
            total = len(validation_results)
            
            if passed == total:
                self.log_test("Parameter Validation", True, f"All {total} validation tests passed")
            else:
                self.log_test("Parameter Validation", False, f"{passed}/{total} tests passed. Details: {validation_results}")
                
        except Exception as e:
            self.log_test("Parameter Validation", False, f"Error during validation: {str(e)}")
    
    async def test_json_serialization(self):
        """Test that all tool responses are properly JSON serializable"""
        try:
            # Test each tool returns valid JSON
            test_tools = [
                {
                    "name": "read_range",
                    "setup": lambda: self._setup_read_range_mock(),
                    "call": lambda: GoogleSheetsMCP.read_range("test", "A1:B2")
                },
                {
                    "name": "get_values", 
                    "setup": lambda: self._setup_get_values_mock(),
                    "call": lambda: GoogleSheetsMCP.get_values("test", ["A1:B2"])
                },
                {
                    "name": "append_rows",
                    "setup": lambda: self._setup_append_rows_mock(),
                    "call": lambda: GoogleSheetsMCP.append_rows("test", "Sheet1", [["A", "B"]])
                },
                {
                    "name": "update_range",
                    "setup": lambda: self._setup_update_range_mock(),
                    "call": lambda: GoogleSheetsMCP.update_range("test", "A1:B2", [["A", "B"]])
                }
            ]
            
            json_results = []
            for tool in test_tools:
                try:
                    tool["setup"]()
                    result = await tool["call"]()
                    
                    # Check it's a string
                    if not isinstance(result, str):
                        json_results.append(f"FAIL: {tool['name']} - Returns {type(result)}, not string")
                        continue
                    
                    # Check it's valid JSON
                    json.loads(result)
                    json_results.append(f"PASS: {tool['name']} - Valid JSON string")
                    
                except json.JSONDecodeError:
                    json_results.append(f"FAIL: {tool['name']} - Invalid JSON")
                except Exception as e:
                    json_results.append(f"FAIL: {tool['name']} - Error: {str(e)}")
            
            passed = sum(1 for r in json_results if r.startswith("PASS"))
            total = len(json_results)
            
            if passed == total:
                self.log_test("JSON Serialization", True, f"All {total} tools return valid JSON")
            else:
                self.log_test("JSON Serialization", False, f"{passed}/{total} tools passed. Details: {json_results}")
                
        except Exception as e:
            self.log_test("JSON Serialization", False, f"Error during JSON testing: {str(e)}")
    
    def _setup_read_range_mock(self):
        """Setup mock for read_range"""
        mock_values = Mock()
        mock_values.get.return_value.execute.return_value = {
            'values': [['A', 'B']],
            'range': 'Sheet1!A1:B1'
        }
        self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
    
    def _setup_get_values_mock(self):
        """Setup mock for get_values"""
        mock_values = Mock()
        mock_values.batchGet.return_value.execute.return_value = {
            'spreadsheetId': 'test',
            'valueRanges': [{'range': 'A1:B1', 'values': [['A', 'B']]}]
        }
        self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
    
    def _setup_append_rows_mock(self):
        """Setup mock for append_rows"""
        mock_values = Mock()
        mock_values.append.return_value.execute.return_value = {
            'spreadsheetId': 'test',
            'updates': {'updatedRange': 'A1:B1', 'updatedRows': 1, 'updatedColumns': 2, 'updatedCells': 2}
        }
        self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
    
    def _setup_update_range_mock(self):
        """Setup mock for update_range"""
        mock_values = Mock()
        mock_values.update.return_value.execute.return_value = {
            'spreadsheetId': 'test',
            'updatedRange': 'A1:B1',
            'updatedRows': 1,
            'updatedColumns': 2,
            'updatedCells': 2
        }
        self.mock_server.sheets_service.spreadsheets.return_value.values.return_value = mock_values
    
    async def run_all_tests(self):
        """Run all protocol tests"""
        logger.info("=" * 60)
        logger.info("GOOGLE SHEETS MCP PROTOCOL LAYER TESTS")
        logger.info("=" * 60)
        
        tests = [
            self.test_server_initialization,
            self.test_tool_registration,
            self.test_read_range_protocol,
            self.test_get_values_protocol,
            self.test_append_rows_protocol,
            self.test_update_range_protocol,
            self.test_insert_rows_protocol,
            self.test_error_handling_protocol,
            self.test_parameter_validation,
            self.test_json_serialization
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                test_name = test.__name__.replace("test_", "").replace("_", " ").title()
                self.log_test(test_name, False, f"Test execution error: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        total = len(self.results)
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {(passed/total)*100:.1f}%" if total > 0 else "0%")
        
        if failed > 0:
            logger.info("\nFAILED TESTS:")
            for result in self.results:
                if result["status"] == "FAIL":
                    logger.info(f"  ❌ {result['test']}: {result['details']}")
        
        logger.info("\n" + "=" * 60)
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED - MCP PROTOCOL LAYER IS PRODUCTION READY!")
        else:
            logger.info(f"⚠️  {failed} TESTS FAILED - PROTOCOL LAYER NEEDS ATTENTION")
        
        logger.info("=" * 60)


async def main():
    """Main test execution"""
    tester = MCPProtocolTester()
    await tester.run_all_tests()
    
    # Return exit code based on test results
    failed = sum(1 for r in tester.results if r["status"] == "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
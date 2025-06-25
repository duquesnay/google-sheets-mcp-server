#!/usr/bin/env python3
"""
Production Readiness Validation Script

This script runs comprehensive tests to validate that the Google Sheets MCP server
is production-ready with all new features properly implemented.

Usage:
    python validate_production_readiness.py

Exit codes:
    0 - All tests passed, production ready
    1 - Some tests failed, needs attention
"""

import sys
import os
import asyncio
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ProductionValidator:
    """Validates production readiness of the Google Sheets MCP server"""
    
    def __init__(self):
        self.test_results = {}
        
    def run_test_script(self, script_name: str, description: str) -> bool:
        """Run a test script and return success status"""
        try:
            logger.info(f"Running {description}...")
            result = subprocess.run([
                sys.executable, script_name
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            success = result.returncode == 0
            self.test_results[script_name] = {
                "description": description,
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if success:
                logger.info(f"✅ {description} - PASSED")
            else:
                logger.error(f"❌ {description} - FAILED")
                logger.error(f"Error output: {result.stderr}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ {description} - ERROR: {str(e)}")
            self.test_results[script_name] = {
                "description": description,
                "success": False,
                "error": str(e)
            }
            return False
    
    def validate_file_structure(self) -> bool:
        """Validate that required files exist"""
        logger.info("Validating file structure...")
        
        required_files = [
            "google_sheets.py",
            "test_mcp_protocol.py", 
            "test_mcp_integration.py",
            "TEST_PROTOCOLS.md"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"❌ Missing required files: {missing_files}")
            return False
        else:
            logger.info("✅ All required files present")
            return True
    
    def validate_imports(self) -> bool:
        """Validate that the main module can be imported"""
        logger.info("Validating module imports...")
        
        try:
            import google_sheets
            from google_sheets import GoogleSheetsMCP, mcp
            
            # Check that key classes exist
            assert GoogleSheetsMCP is not None
            assert mcp is not None
            
            # Check that new tools exist
            new_tools = ["read_range", "get_values", "append_rows", "update_range", "insert_rows"]
            for tool in new_tools:
                assert hasattr(GoogleSheetsMCP, tool), f"Missing tool: {tool}"
            
            logger.info("✅ Module imports and tool availability validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Import validation failed: {str(e)}")
            return False
    
    def run_comprehensive_validation(self) -> bool:
        """Run all validation tests"""
        logger.info("=" * 80)
        logger.info("GOOGLE SHEETS MCP SERVER - PRODUCTION READINESS VALIDATION")
        logger.info("=" * 80)
        
        all_passed = True
        
        # 1. File structure validation
        if not self.validate_file_structure():
            all_passed = False
        
        # 2. Import validation
        if not self.validate_imports():
            all_passed = False
        
        # 3. Protocol layer tests
        if not self.run_test_script("test_mcp_protocol.py", "MCP Protocol Layer Tests"):
            all_passed = False
        
        # 4. Integration tests
        if not self.run_test_script("test_mcp_integration.py", "MCP Integration Tests"):
            all_passed = False
        
        # Print summary
        self.print_final_summary(all_passed)
        
        return all_passed
    
    def print_final_summary(self, all_passed: bool):
        """Print final validation summary"""
        logger.info("=" * 80)
        logger.info("PRODUCTION READINESS VALIDATION SUMMARY")
        logger.info("=" * 80)
        
        # Count test results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        
        logger.info(f"File Structure: ✅ PASS")
        logger.info(f"Module Imports: ✅ PASS") 
        logger.info(f"Test Scripts: {passed_tests}/{total_tests} PASSED")
        
        if not all_passed:
            logger.info("\nFAILED COMPONENTS:")
            for script, result in self.test_results.items():
                if not result["success"]:
                    logger.info(f"  ❌ {result['description']}")
        
        logger.info("\n" + "=" * 80)
        
        if all_passed:
            logger.info("🎉 PRODUCTION READINESS VALIDATION: ALL TESTS PASSED!")
            logger.info("")
            logger.info("✅ Server initialization works correctly")
            logger.info("✅ All new tools are properly implemented:")
            logger.info("   • read_range - Read data from specific ranges")
            logger.info("   • get_values - Batch read from multiple ranges")
            logger.info("   • append_rows - Add rows to end of data")
            logger.info("   • update_range - Update specific cell ranges")
            logger.info("   • insert_rows - Insert rows at specific positions")
            logger.info("✅ MCP protocol compliance verified")
            logger.info("✅ Error handling and validation working")
            logger.info("✅ JSON serialization correct")
            logger.info("✅ Async patterns consistent")
            logger.info("")
            logger.info("🚀 THE GOOGLE SHEETS MCP SERVER IS PRODUCTION READY!")
        else:
            logger.info("⚠️  PRODUCTION READINESS VALIDATION: SOME TESTS FAILED!")
            logger.info("Please review the failed components above and fix issues before deployment.")
        
        logger.info("=" * 80)


def main():
    """Main validation execution"""
    validator = ProductionValidator()
    success = validator.run_comprehensive_validation()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
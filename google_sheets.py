#!/usr/bin/env python3
"""
Google Sheets MCP Server

A Model Context Protocol server for Google Sheets that can be used directly with Claude Desktop.
"""
import os
import sys
import json
import logging
import argparse
from typing import Dict, List, Optional, Any, Union, TypedDict
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache

import uvicorn
from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource, Annotations
from mcp import McpError
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

class Settings(BaseSettings):
    """Server configuration settings"""
    GOOGLE_SERVICE_ACCOUNT_PATH: str | None = None
    GOOGLE_CREDENTIALS_PATH: str = "~/.config/google_sheets_mcp/google-sheets-mcp.json"
    GOOGLE_TOKEN_PATH: str = "~/.config/google_sheets_mcp/token.json"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    class Config:
        env_prefix = "GOOGLE_SHEETS_MCP_"

class GoogleSheetsError(Exception):
    """Base exception for Google Sheets operations"""
    pass

class CredentialsError(GoogleSheetsError):
    """Raised when there are issues with credentials"""
    pass

class SheetNotFoundError(GoogleSheetsError):
    """Raised when a sheet is not found"""
    pass

class SheetRange(BaseModel):
    sheet_name: str
    cell_range: str
    
    def to_a1_notation(self) -> str:
        return f"'{self.sheet_name}'!{self.cell_range}"

# Create the MCP server instance
mcp = FastMCP("Google Sheets MCP")

class GoogleSheetsMCP:
    """
    Google Sheets MCP Server implementation
    """
    def __init__(self, service_account_path: Optional[str] = None):
        """
        Initialize the Google Sheets MCP Server
        
        Args:
            service_account_path: Path to service account JSON file
        """
        self.service_account_path = service_account_path
        self.sheets_service = None
        self.drive_service = None
        self._initialize_services()
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_api_request(self, request_func, *args, **kwargs):
        """Make an API request with retries"""
        try:
            return await request_func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status in [429, 500, 502, 503, 504]:
                raise  # Retry on these status codes
            raise  # Don't retry on other errors

    def _initialize_services(self):
        """Initialize Google API services"""
        try:
            credentials = self._get_credentials()
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to initialize Google services: {str(e)}")
            # Don't fail initialization - we'll check for services before use
    
    def _get_credentials(self):
        """Get Google API credentials"""
        # Try service account first
        if self.service_account_path and os.path.exists(self.service_account_path):
            try:
                return service_account.Credentials.from_service_account_file(
                    self.service_account_path, scopes=SCOPES
                )
            except Exception as e:
                logger.error(f"Error loading service account credentials: {str(e)}")
        
        # Fall back to user OAuth if available
        token_path = os.path.expanduser("~/.config/google_sheets_mcp/token.json")
        credentials_path = os.path.expanduser("~/.config/google_sheets_mcp/google-sheets-mcp.json")
        
        credentials = None
        if os.path.exists(token_path):
            try:
                credentials = Credentials.from_authorized_user_info(
                    json.loads(open(token_path).read()), SCOPES
                )
            except Exception:
                logger.warning("Failed to load token, will attempt to create new one")
        
        # If no valid credentials available, prompt the user to log in
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    logger.error(f"No credentials available. Please provide a service account or OAuth credentials.")
                    raise FileNotFoundError("No Google API credentials available")
                    
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                credentials = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, 'w') as token:
                    token.write(credentials.to_json())
        
        return credentials
            
    async def list_files(
        self, 
        path: str = "", 
        page_size: int = 100,
        page_token: Optional[str] = None
    ) -> List[Resource]:
        """
        List Google Sheets as files
        
        Args:
            path: Path to list (ignored for Google Sheets)
            page_size: Number of files to return per page
            page_token: Token to use for pagination
            
        Returns:
            List of Resource objects
        """
        if not self.drive_service:
            self._initialize_services()
            if not self.drive_service:
                raise HTTPException(status_code=500, detail="Google Drive service unavailable")
                
        try:
            # Search for Google Sheets files
            results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=page_size,
                pageToken=page_token,
                fields="files(id, name, createdTime, modifiedTime, owners)"
            ).execute()
            
            sheets = results.get('files', [])
            
            # Convert to MCP Resource objects
            files = []
            for sheet in sheets:
                files.append(Resource(
                    uri=f"sheets://{sheet.get('id')}",
                    name=sheet.get("name"),
                    mimeType="application/vnd.google-apps.spreadsheet",
                    size=None,  # Size not applicable for Google Sheets
                    annotations=Annotations(
                        modified_at=sheet.get("modifiedTime"),
                        created_at=sheet.get("createdTime")
                    )
                ))
            
            return files
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to list Google Sheets: {str(e)}")
    
    async def read_file(self, file_id: str, query: Dict[str, Any] = None) -> str:
        """
        Read Google Sheet data
        
        Args:
            file_id: Google Sheet ID or path
            query: Query parameters
            
        Returns:
            Sheet data as JSON string
        """
        if not self.sheets_service:
            self._initialize_services()
            if not self.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            # Parse file_id to extract sheet_id, sheet_name, and range
            if '/' in file_id:
                parts = file_id.strip('/').split('/')
                sheet_id = parts[0]
                sheet_name = parts[1] if len(parts) > 1 else ""
                cell_range = parts[2] if len(parts) > 2 else "A1"
            else:
                sheet_id = file_id
                sheet_name = ""
                cell_range = "A1"
                
            # Build range_name
            if sheet_name and cell_range:
                range_name = f"'{sheet_name}'!{cell_range}"
            else:
                range_name = cell_range
                
            # Process query parameters
            if query:
                # Override range if specified in query
                if 'range' in query:
                    range_name = query['range']
                    
                # Add sheet name to range if provided
                if sheet_name and 'range' in query and not query['range'].startswith(f"'{sheet_name}'!"):
                    range_name = f"'{sheet_name}'!{query['range']}"
                    
            # Set options
            value_render_option = query.get('valueRenderOption', 'FORMATTED_VALUE') if query else 'FORMATTED_VALUE'
            date_time_render_option = query.get('dateTimeRenderOption', 'FORMATTED_STRING') if query else 'FORMATTED_STRING'
            
            # Read from sheet
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name,
                valueRenderOption=value_render_option,
                dateTimeRenderOption=date_time_render_option
            ).execute()
            
            values = result.get('values', [])
            
            # Process data
            if not values:
                return json.dumps([])
                
            # If the first row might be headers
            if query and query.get('headers', 'true').lower() in ('true', '1', 't'):
                if len(values) > 0:
                    headers = values[0]
                    data = []
                    
                    for row in values[1:]:
                        # Pad the row if it's shorter than headers
                        padded_row = row + [''] * (len(headers) - len(row))
                        data.append(dict(zip(headers, padded_row)))
                        
                    return json.dumps(data)
            
            # Return as 2D array
            return json.dumps(values)
            
        except HttpError as error:
            if error.resp.status == 404:
                raise McpError(f"Sheet with ID {sheet_id} not found")
            logger.error(f"Google API error: {str(error)}")
            raise HTTPException(status_code=error.resp.status, detail=str(error))
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    
    async def write_file(self, file_id: str, content: str) -> str:
        """
        Write data to a Google Sheet
        
        Args:
            file_id: Google Sheet ID or path
            content: Data to write (JSON string)
            
        Returns:
            Result of write operation
        """
        if not self.sheets_service:
            self._initialize_services()
            if not self.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            # Parse file_id to extract sheet_id, sheet_name, and range
            if '/' in file_id:
                parts = file_id.strip('/').split('/')
                sheet_id = parts[0]
                sheet_name = parts[1] if len(parts) > 1 else "Sheet1"
                cell_range = parts[2] if len(parts) > 2 else "A1"
            else:
                sheet_id = file_id
                sheet_name = "Sheet1"
                cell_range = "A1"
                
            # Build range_name
            if sheet_name and cell_range:
                range_name = f"'{sheet_name}'!{cell_range}"
            else:
                range_name = cell_range
            
            # Parse the content
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                data = [[content]]
            
            # Convert to 2D array
            if isinstance(data, dict):
                # Convert dict to array of key-value pairs
                values = [["Key", "Value"]] + [[k, str(v)] for k, v in data.items()]
            elif isinstance(data, list):
                if data and all(isinstance(item, dict) for item in data):
                    # Array of objects - extract keys from first object
                    keys = list(data[0].keys())
                    values = [keys] + [[str(item.get(k, '')) for k in keys] for item in data]
                elif data and all(isinstance(item, list) for item in data):
                    # Already a 2D array
                    values = [[str(cell) if cell is not None else '' for cell in row] for row in data]
                else:
                    # 1D array, make it a column
                    values = [[str(item)] for item in data]
            else:
                # Single value
                values = [[str(data)]]
            
            # Write to sheet
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": values}
            ).execute()
            
            return json.dumps({
                "updated_cells": result.get('updatedCells'),
                "updated_rows": result.get('updatedRows'),
                "updated_columns": result.get('updatedColumns'),
                "updated_range": result.get('updatedRange')
            })
            
        except HttpError as error:
            if error.resp.status == 404:
                raise McpError(f"Sheet with ID {sheet_id} not found")
            logger.error(f"Google API error: {str(error)}")
            raise HTTPException(status_code=error.resp.status, detail=str(error))
        except Exception as e:
            logger.error(f"Error writing file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")
    
    async def search_files(self, query: str) -> List[Resource]:
        """
        Search for Google Sheets
        
        Args:
            query: Search query string
            
        Returns:
            List of matching Resource objects
        """
        if not self.drive_service:
            self._initialize_services()
            if not self.drive_service:
                raise HTTPException(status_code=500, detail="Google Drive service unavailable")
                
        try:
            # Search for Google Sheets files by name
            q = f"mimeType='application/vnd.google-apps.spreadsheet' and name contains '{query}'"
            results = self.drive_service.files().list(
                q=q,
                pageSize=100,
                fields="files(id, name, createdTime, modifiedTime, owners)"
            ).execute()
            
            sheets = results.get('files', [])
            
            # Convert to MCP Resource objects
            files = []
            for sheet in sheets:
                files.append(Resource(
                    uri=f"sheets://{sheet.get('id')}",
                    name=sheet.get("name"),
                    mimeType="application/vnd.google-apps.spreadsheet",
                    size=None,  # Size not applicable for Google Sheets
                    annotations=Annotations(
                        modified_at=sheet.get("modifiedTime"),
                        created_at=sheet.get("createdTime")
                    )
                ))
            
            return files
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to search files: {str(e)}")

    @staticmethod
    @mcp.tool(
        name="create_sheet",
        description="Create a new Google Sheet"
    )
    async def create_sheet(title: str) -> str:
        """Create a new Google Sheet"""
        # Get the instance from the global mcp instance
        instance = mcp._instance
        if not instance:
            raise HTTPException(status_code=500, detail="MCP instance not initialized")
            
        try:
            # Ensure services are initialized
            instance._initialize_services()
            if not instance.sheets_service:
                raise HTTPException(status_code=500, detail="Failed to initialize Google Sheets service")
                
            spreadsheet = {
                'properties': {
                    'title': title
                }
            }
            spreadsheet = instance.sheets_service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()
            return json.dumps({"spreadsheetId": spreadsheet.get('spreadsheetId')})
        except Exception as e:
            logger.error(f"Error creating sheet: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    @mcp.tool(
        name="format_range",
        description="Format a range of cells in a sheet"
    )
    async def format_range(file_id: str, range: str, format: dict) -> str:
        """Format a range of cells in a sheet"""
        instance = mcp._instance
        if not instance.sheets_service:
            instance._initialize_services()
            if not instance.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            requests = [{
                'repeatCell': {
                    'range': {'sheetId': 0, 'range': range},
                    'cell': {'userEnteredFormat': format},
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            }]
            instance.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=file_id,
                body={'requests': requests}
            ).execute()
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"Error formatting range: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    @mcp.tool(
        name="write_formula",
        description="Write a formula to a range of cells"
    )
    async def write_formula(file_id: str, range: str, formula: str) -> str:
        """Write a formula to a range of cells"""
        instance = mcp._instance
        if not instance.sheets_service:
            instance._initialize_services()
            if not instance.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            values = [[{'userEnteredValue': {'formulaValue': formula}}]]
            instance.sheets_service.spreadsheets().values().update(
                spreadsheetId=file_id,
                range=range,
                valueInputOption='USER_ENTERED',
                body={'values': values}
            ).execute()
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"Error writing formula: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    @mcp.tool(
        name="add_sheet",
        description="Add a new sheet to an existing spreadsheet"
    )
    async def add_sheet(file_id: str, title: str) -> str:
        """Add a new sheet to an existing spreadsheet"""
        instance = mcp._instance
        if not instance.sheets_service:
            instance._initialize_services()
            if not instance.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': title
                    }
                }
            }]
            instance.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=file_id,
                body={'requests': requests}
            ).execute()
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"Error adding sheet: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    @mcp.tool(
        name="delete_sheet",
        description="Delete a sheet from a spreadsheet"
    )
    async def delete_sheet(file_id: str, sheet_id: int) -> str:
        """Delete a sheet from a spreadsheet"""
        instance = mcp._instance
        if not instance.sheets_service:
            instance._initialize_services()
            if not instance.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            requests = [{
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            }]
            instance.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=file_id,
                body={'requests': requests}
            ).execute()
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"Error deleting sheet: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    @mcp.tool(
        name="get_sheet_properties",
        description="Get properties of all sheets in a spreadsheet"
    )
    @lru_cache(maxsize=100)
    async def get_sheet_properties(file_id: str) -> str:
        """Get properties of all sheets in a spreadsheet"""
        instance = mcp._instance
        if not instance.sheets_service:
            instance._initialize_services()
            if not instance.sheets_service:
                raise HTTPException(status_code=500, detail="Google Sheets service unavailable")
                
        try:
            spreadsheet = instance.sheets_service.spreadsheets().get(
                spreadsheetId=file_id,
                fields='sheets.properties'
            ).execute()
            return json.dumps(spreadsheet.get('sheets', []))
        except Exception as e:
            logger.error(f"Error getting sheet properties: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Google Sheets MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server to")
    parser.add_argument("--service-account", help="Path to service account JSON file")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--credentials-path", help="Path to OAuth credentials file")
    parser.add_argument("--token-path", help="Path to OAuth token file")
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    # Create settings from command line arguments
    settings = Settings(
        GOOGLE_SERVICE_ACCOUNT_PATH=args.service_account,
        GOOGLE_CREDENTIALS_PATH=args.credentials_path or "~/.config/google_sheets_mcp/google-sheets-mcp.json",
        GOOGLE_TOKEN_PATH=args.token_path or "~/.config/google_sheets_mcp/token.json",
        HOST=args.host,
        PORT=args.port,
        LOG_LEVEL=args.log_level
    )
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Create MCP server
    mcp_server = GoogleSheetsMCP(service_account_path=settings.GOOGLE_SERVICE_ACCOUNT_PATH)
    
    # Store the instance in the mcp object
    mcp._instance = mcp_server
    
    # Initialize services before starting
    try:
        mcp_server._initialize_services()
        if not mcp_server.sheets_service:
            logger.error("Failed to initialize Google Sheets service")
            sys.exit(1)
        logger.info("Successfully initialized Google Sheets service")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        sys.exit(1)
    
    # Start server using mcp.run()
    logger.info(f"Starting Google Sheets MCP Server")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
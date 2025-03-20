# Google Sheets MCP Server

A Model Context Protocol (MCP) server for Google Sheets that enables Claude Desktop to interact with Google Sheets directly. This server provides tools for creating, reading, writing, and managing Google Sheets through Claude Desktop.

## Features

- Create new Google Sheets
- Read and write data to existing sheets
- Format cells and ranges
- Add and delete sheets
- Write formulas
- Search for sheets
- List available sheets

## Prerequisites

- Python 3.10 or higher
- Google Cloud Project with Google Sheets API enabled
- OAuth 2.0 credentials from Google Cloud Console
- Claude Desktop application
- `uv` package manager (recommended)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/google-sheets-mcp-server.git
cd google-sheets-mcp-server
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies using `uv`:

```bash
uv pip install -e .
```

4. Set up Google Cloud credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Sheets API and Google Drive API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download the credentials and save as `~/.config/google_sheets_mcp/google-sheets-mcp.json`

## Configuration

1. Configure Claude Desktop:
   - Open Claude Desktop settings
   - Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google_sheets": {
      "command": "/path/to/your/.venv/bin/python",
      "args": [
        "/path/to/your/google_sheets.py",
        "--credentials-path",
        "/Users/yourusername/.config/google_sheets_mcp/google-sheets-mcp.json",
        "--log-level",
        "DEBUG"
      ]
    }
  }
}
```

2. First-time setup:
   - Run the server manually to complete OAuth authentication:

```bash
python google_sheets.py --credentials-path ~/.config/google_sheets_mcp/google-sheets-mcp.json
```

- Follow the browser prompts to authorize the application
- The token will be saved automatically for future use

## Usage

After setup, you can use the following commands in Claude Desktop:

- Create a new sheet: `create_sheet(title: str)`
- Format cells: `format_range(file_id: str, range: str, format: dict)`
- Write formulas: `write_formula(file_id: str, range: str, formula: str)`
- Add sheets: `add_sheet(file_id: str, title: str)`
- Delete sheets: `delete_sheet(file_id: str, sheet_id: int)`
- Get sheet properties: `get_sheet_properties(file_id: str)`

## Development

### Project Structure

```
google-sheets-mcp-server/
├── .venv/                  # Virtual environment
├── google_sheets.py        # Main server implementation
├── pyproject.toml         # Project configuration and dependencies
├── tests/                 # Test files
└── README.md             # This file
```

### Adding New Features

1. Add new tool methods to the `GoogleSheetsMCP` class
2. Decorate them with `@mcp.tool()`
3. Update the README with new feature documentation

### Running Tests

```bash
pytest
```

## Troubleshooting

1. **Server Connection Issues**

   - Check if the server is running
   - Verify credentials path in config
   - Check logs in Claude Desktop

2. **Authentication Issues**

   - Ensure OAuth credentials are valid
   - Check if your email is added as a test user
   - Try deleting token.json and re-authenticating

3. **API Errors**
   - Verify Google Sheets API is enabled
   - Check API quotas and limits
   - Review error logs for specific issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

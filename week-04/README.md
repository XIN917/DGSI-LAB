# Week 4 Function Calling Assignment

A complete implementation of multi-turn function calling with Claude/Qwen LLM, featuring SQL query execution and file downloads with user confirmation.

## Features

✅ **Multi-turn Function Calling** — Continuous conversation with the AI handling multiple function calls  
✅ **Execute SQL Tool** — Simulated database operations (SELECT, INSERT, UPDATE, DELETE)  
✅ **Wget Download Tool** — Download files with built-in user confirmation  
✅ **Error Handling** — Comprehensive error handling for API, network, and user errors  
✅ **Environment Configuration** — Secure API key and endpoint management via `.env`  
✅ **Production Ready** — Full type hints, docstrings, and best practices  

## Project Structure

```
.
├── main.py              # Main application (Steps 1-5)
├── pyproject.toml       # uv project configuration
├── .env                 # Environment variables (API key, endpoint, model)
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Requirements

- **Python 3.9+**
- **uv** package manager — [Install here](https://docs.astral.sh/uv/getting-started/installation/)
- **wget** for file downloads — Pre-installed on macOS via `brew install wget`
- **Internet connection** for API calls

## Quick Start

```bash
# 1. Navigate to the project
cd /Users/xin/UPC/2025-Q2/DGSI/week-04

# 2. Install dependencies (one-time)
uv sync

# 3. Run the program
uv run python main.py
```

## Setup Instructions

### 1. Clone or Download the Project

```bash
# If cloning
git clone <repository-url>
cd week-04-function-calling

# Or if you have this directory already
cd /Users/xin/UPC/2025-Q2/DGSI/week-04
```

### 2. Install Dependencies with `uv`

```bash
# Create virtual environment and install dependencies
uv sync

# This automatically:
# - Creates a .venv directory
# - Installs openai, python-dotenv, and requests
# - Locks dependencies in uv.lock
```

### 3. Configure Environment Variables

Edit the `.env` file in the project directory with your API credentials:

```
OPENAI_API_KEY=your_api_key_here
OPENAI_API_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
MODEL=qwen3.5-122b-a10b
```

**Required Variables:**
- `OPENAI_API_KEY` — Your API key (keep secret, never commit to git)
- `OPENAI_API_ENDPOINT` — API endpoint URL
- `MODEL` — Model identifier (e.g., `qwen3.5-122b-a10b`)

### 4. Verify Setup

```bash
# Activate the virtual environment
source .venv/bin/activate

# Test the setup
uv run python main.py
```

## Running the Program

### Option 1: Using `uv run` (Recommended)

```bash
uv run python main.py
```

### Option 2: Using Python Directly

```bash
source .venv/bin/activate
python main.py
```

## Example Interaction

```
======================================================================
Week 4 Function Calling Assistant
======================================================================
Commands you can try:
  - 'List all users from the database'
  - 'Download a file from https://www.example.com/file.txt'
  - 'How many rows are in the users table?'
  - 'quit' or 'exit' to end the conversation
======================================================================

You: List all users from the database

🔧 Calling tool: execute_sql
   Arguments: {"query": "SELECT * FROM users"}
   Result: {"result": "rows", "data": [
     {"id": 1, "name": "Alice", "email": "alice@example.com"},
     {"id": 2, "name": "Bob", "email": "bob@example.com"},
     {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
   ]}
```

## Implementation Overview

### Step 1: Project Setup & Configuration

The project uses `uv` for dependency management and `python-dotenv` for environment configuration:

- **Dependencies** are specified in `pyproject.toml`
- **Environment variables** loaded from `.env` in `load_config()`
- **OpenAI client** initialized with custom endpoint support

### Step 2: Tool Definitions

Two main tools are implemented for function calling:

#### 1. `execute_sql(query: str) -> str`
- Simulates SQL database operations
- Supports: SELECT, INSERT, UPDATE, DELETE, CREATE TABLE
- Returns JSON with results or errors
- Real implementation would connect to actual database

#### 2. `wget_file(url: str, output_path: Optional[str]) -> str`
- Downloads files from URLs using `wget` command
- **Requires user confirmation** before download
- Supports custom output paths
- Error handling for invalid URLs, timeouts, missing `wget`

### Step 3: Function Calling with Tools

Tools are defined in OpenAI's function calling format with:
- Function name and description
- Parameter schema (type, properties, required fields)
- Proper error messages

The `TOOLS` list contains tool definitions sent to the API.

### Step 4: Multi-turn Conversation Loop

The main loop implements:
- Continuous conversation with user input
- Automatic tool call detection and execution
- Recursive API calls until response is complete
- Proper message history management

```python
while True:
    user_input = input("You: ")
    messages.append({"role": "user", "content": user_input})
    
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        
        if response.choices[0].finish_reason == "stop":
            # Response complete
            break
        elif response.choices[0].finish_reason == "tool_calls":
            # Process tool calls and continue
            ...
```

### Step 5: Error Handling

Comprehensive error handling for:
- **API Errors** (`APIError`) — API key, endpoint, rate limits
- **File Operations** — Missing wget, download timeouts
- **Input Parsing** — Invalid JSON from tool arguments
- **User Input** — EOF, Ctrl+C, empty input
- **Network Issues** — URL validation, connection timeouts

All errors provide clear user feedback without crashing.

## Tool Specifications

### execute_sql

**Purpose:** Execute SQL queries against a simulated database

**Parameters:**
- `query` (string, required) — SQL query to execute

**Returns:**
```json
{
  "result": "rows|success|count|error",
  "data": [...],      // For SELECT queries
  "affected_rows": 1, // For INSERT/UPDATE/DELETE
  "error": "..."      // For errors
}
```

**Examples:**
```python
execute_sql("SELECT * FROM users")
execute_sql("INSERT INTO users (name) VALUES ('Alice')")
execute_sql("UPDATE users SET name='Bob' WHERE id=2")
```

### wget_file

**Purpose:** Download files from URLs with user confirmation

**Parameters:**
- `url` (string, required) — URL to download
- `output_path` (string, optional) — Output file path

**Flow:**
1. Display download confirmation prompt
2. Wait for user response (yes/no)
3. If approved, execute `wget` command
4. Return success/error status

**Returns:**
```json
{
  "result": "success|error|cancelled",
  "message": "Download successful",
  "url": "https://...",
  "filename": "file.txt"
}
```

## Troubleshooting

### Issue: "Missing required environment variables"

**Solution:** Ensure `.env` file contains:
```
OPENAI_API_KEY=your_key
OPENAI_API_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
MODEL=qwen3.5-122b-a10b
```

### Issue: "wget command not found"

**Solution:** Install wget on macOS:
```bash
brew install wget
```

### Issue: "ModuleNotFoundError: No module named 'openai'"

**Solution:** Reinstall dependencies:
```bash
uv sync  # or pip install -r requirements.txt
```

### Issue: Download fails with timeout

**Solution:** Check internet connection and try a smaller file

### Issue: API returns "Unauthorized" error

**Solution:** Verify `OPENAI_API_KEY` is valid and has access to the endpoint

## Project Architecture

```
┌─────────────────────────────────────────┐
│         User Input (CLI)                │
└────────────────────┬────────────────────┘
                     ↓
         ┌─────────────────────────┐
         │  Main Conversation Loop │
         └────────────┬────────────┘
                      ↓
    ┌─────────────────────────────────┐
    │  Send to LLM with Functions     │
    │  (OpenAI-compatible endpoint)   │
    └────────────────┬────────────────┘
                     ↓
         ┌───────────────────────────┐
         │  Parse LLM Response       │
         └──┬────────────────────────┘
            ↓
    ┌───────────────────┐
    │ Tool Calls?       │
    └─┬──────────────┬──┘
      │              │
    YES             NO
      ↓              ↓
Execute        Return Response
Tools          to User
      ↓
┌──────────────┐
│ execute_sql  │
│ wget_file    │
└──────┬───────┘
       ↓
Return Results
(back to loop)
```

## Git Setup

Create a `.gitignore` to exclude sensitive files:

```
.env
.venv/
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.DS_Store
*.swp
.idea/
```

Then commit and push:

```bash
git add .
git commit -m "Initial commit: Week 4 function calling assignment"
git push origin main
```

## Key Technologies

- **openai** — OpenAI-compatible API client
- **python-dotenv** — Environment variable management
- **uv** — Modern Python package manager
- **subprocess** — Execute system commands (wget)

## Learning Outcomes

After completing this assignment, you should understand:

1. ✓ How function calling works with LLMs
2. ✓ Multi-turn conversation management
3. ✓ Error handling and recovery in AI applications
4. ✓ Integration with external tools and APIs
5. ✓ Building interactive CLI applications
6. ✓ Managing dependencies with modern tools (uv)

## Next Steps

To extend this project:

1. **Real Database** — Replace simulated SQL with actual database (SQLite, PostgreSQL)
2. **More Tools** — Add email sending, web scraping, file operations
3. **Conversation Memory** — Save chat history to file
4. **Web Interface** — Convert to Flask/FastAPI web app
5. **Logging** — Add structured logging for debugging
6. **Testing** — Add unit tests for tools and error cases

## License

Educational use - Week 4 DGSI Course

## Support

For issues or questions:
1. Check `.env` configuration
2. Verify API credentials are valid
3. Ensure internet connection
4. Check program output for specific error messages
5. Review error handling section in main.py
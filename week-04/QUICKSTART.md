# Quick Start Guide

Get up and running in 3 steps:

## Step 1: Install Dependencies

```bash
cd /Users/xin/UPC/2025-Q2/DGSI/week-04
uv sync
```

Expected output:
```
Resolved 24 packages
Installed 4 packages
```

## Step 2: Verify Setup

```bash
source .venv/bin/activate
python test_tools.py
```

Expected output:
```
✓ All tests passed!
Now you can run: uv run python main.py
```

## Step 3: Run the Program

```bash
uv run python main.py
```

You should see the assistant prompt:
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

You: _
```

## What Happens Next?

1. Type a command
2. The AI processes your request
3. If it needs to use a tool (SQL or wget), it will:
   - Call the tool automatically
   - Show you what it's doing with 🔧
   - Display the results
4. Type "quit" or "exit" to end

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `command not found: uv` | Install uv: `pip install uv` or `brew install uv` |
| `ModuleNotFoundError` | Run `uv sync` again |
| API errors | Check `.env` file has valid API key |
| `wget not found` | Run `brew install wget` |

## Try These Commands

1. **Query the database:**
   - "List all users"
   - "How many rows in users table?"
   - "Insert a new user named Alice"

2. **Download a file:**
   - "Download https://www.example.com/file.txt"
   - (You'll need to confirm the download)

3. **Multiple operations:**
   - "First, list all users, then tell me how many there are"

Enjoy exploring function calling with LLMs!

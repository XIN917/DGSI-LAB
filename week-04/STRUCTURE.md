# Project Structure & File Guide

Complete overview of all project files and their purposes.

## File Directory

```
/Users/xin/UPC/2025-Q2/DGSI/week-04/
│
├── 📄 README.md                    # Main documentation (START HERE)
├── 📄 QUICKSTART.md                # Quick setup in 3 steps
├── 📄 STRUCTURE.md                 # This file - project architecture
│
├── 🐍 main.py                      # Main application (Steps 1-5)
├── 🐍 test_tools.py                # Test suite for all tools
│
├── ⚙️ pyproject.toml               # uv project configuration
├── 📦 uv.lock                      # Dependency lock file (auto-generated)
├── 📦 requirements.txt             # Alternative pip requirements
│
├── 🔐 .env                         # Environment variables (API keys)
├── 🚫 .gitignore                   # Git exclude patterns
│
└── 📁 .venv/                       # Virtual environment (auto-created)
```

## Core Files Description

### 1. **main.py** — Main Application

The complete implementation with all 5 steps:

#### Step 1: Project Setup & Configuration
```python
def load_config() -> tuple[str, str, str]:
    """Load API key, endpoint, model from .env"""

def initialize_client(api_key: str, api_endpoint: str) -> OpenAI:
    """Initialize OpenAI client with custom endpoint"""
```

#### Step 2: Define Tools
```python
def execute_sql(query: str) -> str:
    """Simulate SQL database operations"""

def wget_file(url: str, output_path: Optional[str]) -> str:
    """Download files with user confirmation"""

TOOLS = [...]  # Tool definitions for API
```

#### Step 3: Function Calling Setup
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "...",
            "parameters": {...}
        }
    },
    ...
]

def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Route tool calls to appropriate functions"""
```

#### Step 4: Main Loop (While Loop)
```python
def run_conversation(client: OpenAI, model: str) -> None:
    """Multi-turn conversation with function calling
    
    while True:
        user_input = input("You: ")
        messages.append({"role": "user", "content": user_input})
        
        while True:
            response = client.chat.completions.create(...)
            # Process tool calls, continue until done
    """
```

#### Step 5: Error Handling
- ✓ APIError — API credentials, rate limits
- ✓ FileNotFoundError — Missing wget
- ✓ SubprocessTimeout — Download timeouts
- ✓ JSONDecodeError — Invalid tool arguments
- ✓ KeyboardInterrupt — User interruption

**Size:** ~450 lines | **Type:** Production-ready

### 2. **test_tools.py** — Test Suite

Validates all components work correctly:

```python
def test_execute_sql():
    """Test all SQL operations"""
    # SELECT, COUNT, INSERT, UPDATE, DELETE, CREATE TABLE

def test_config_loading():
    """Test environment configuration"""

def test_client_initialization():
    """Test OpenAI client setup"""
```

**Purpose:** Run before executing main program to catch issues early  
**Size:** ~150 lines | **Type:** Testing/Verification

### 3. **pyproject.toml** — Project Configuration

```toml
[project]
name = "week-04-function-calling"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "openai>=1.3.0",
    "python-dotenv>=1.0.0",
    "requests>=2.31.0",
]
```

**Why:** Tells `uv` how to set up the project  
**Type:** Configuration file  
**Related:** `uv.lock` (generated after `uv sync`)

### 4. **.env** — Environment Secrets

```
OPENAI_API_KEY=sk-...
OPENAI_API_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
MODEL=qwen3.5-122b-a10b
```

**⚠️ SECURITY:**
- Never commit to git (use .gitignore)
- Keep API key secret
- Share only the template, not actual values

### 5. **.gitignore** — Git Configuration

Specifies files to ignore:
```
.env                # Secrets
.venv/               # Virtual environment
__pycache__/        # Python cache
*.pyc               # Compiled Python
*.egg-info/         # Package metadata
.DS_Store           # macOS files
```

## Documentation Files

| File | Content | Audience |
|------|---------|----------|
| **README.md** | Complete guide with all details | Everyone |
| **QUICKSTART.md** | 3-step setup guide | First-time users |
| **STRUCTURE.md** | This file - architecture overview | Developers |

## Dependency Files

| File | Purpose | Auto-generated? |
|------|---------|-----------------|
| **pyproject.toml** | Project metadata and dependencies | No - manually created |
| **uv.lock** | Exact versions of all packages | Yes - `uv sync` creates it |
| **requirements.txt** | Alternative pip format | No - manually created |

## Virtual Environment

After `uv sync`, the `.venv/` directory contains:
- Python interpreter
- All installed packages
- Activation scripts (`bin/activate`)

**Don't commit .venv/** — It's auto-generated and user-specific

## How Files Work Together

```
1. User runs: uv run python main.py

2. uv:
   - Checks pyproject.toml for dependencies
   - Uses .venv/ Python environment
   - Runs main.py

3. main.py:
   - Imports load_config from Step 1
   - Loads API credentials from .env
   - Initializes client from Step 1
   - Defines tools from Step 2
   - Runs conversation loop from Step 4
   - Catches errors from Step 5

4. Tools:
   - execute_sql() — Simulates database
   - wget_file() — Downloads files
   - Both handle errors properly
```

## Setup Timeline

```
GitHub Clone
    ↓
[ls -la] — See pyproject.toml, README, main.py
    ↓
[uv sync] — Creates .venv/, installs dependencies
    ↓
[python test_tools.py] — Validates everything works
    ↓
[uv run python main.py] — Start using!
```

## Key Implementation Details

### Conversation Message Flow

```python
messages = []

# Round 1
messages.append({"role": "user", "content": "Query users"})
response = api_call(messages, tools=TOOLS)
# API calls execute_sql tool

messages.append(response.message)  # Assistant's response
messages.append({"type": "tool_result", "content": "..."})
# Continue if needed...
```

### Tool Calling Architecture

```python
response.finish_reason:
├── "stop" → Response complete, show to user
└── "tool_calls" → Execute tools, continue loop
    ├── tool.function.name → "execute_sql" or "wget_file"
    ├── tool.function.arguments → {"query": "..."}
    └── tool_result → Add to messages, loop again
```

### Error Handling Hierarchy

```python
try:
    client.chat.completions.create(...)  # APIError
except APIError:
    print("API Error")
except subprocess.TimeoutExpired:        # Timeout
    print("Download timeout")
except FileNotFoundError:                # Missing command
    print("wget not found")
except json.JSONDecodeError:             # Parse error
    print("Invalid JSON")
except KeyboardInterrupt:                # User interrupt
    print("Interrupted")
```

## Testing Strategy

```python
# Test all tools independently
execute_sql("SELECT * FROM users")      ✓
load_config()                            ✓
initialize_client(...)                   ✓

# Test integration
run_conversation(client, model)          ← Full program
```

## Extension Points

To add features, modify these sections:

| Feature | File | Location |
|---------|------|----------|
| New tools | main.py | `TOOLS` list, `process_tool_call()` |
| Different API | main.py | `initialize_client()` |
| Store history | main.py | `run_conversation()` |
| Add logging | main.py | Import + function calls |
| Real database | main.py | `execute_sql()` implementation |

## File Sizes

```
main.py              ~450 lines (~15 KB)
test_tools.py        ~150 lines (~4 KB)
README.md            ~350 lines (~15 KB)
QUICKSTART.md        ~80 lines (~3 KB)
pyproject.toml       ~15 lines (~0.3 KB)
requirements.txt     ~3 lines (~0.1 KB)
.gitignore           ~30 lines (~1 KB)
```

## Common Operations

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run program | `uv run python main.py` |
| Run tests | `python test_tools.py` |
| Activate env | `source .venv/bin/activate` |
| Deactivate env | `deactivate` |
| View logs | Check terminal output |
| Update deps | `uv sync` (auto-updates) |

## Next Steps

1. **Read** — Open README.md for full documentation
2. **Test** — Run `python test_tools.py` to verify setup
3. **Run** — Execute `uv run python main.py`
4. **Explore** — Try different prompts with function calling
5. **Extend** — Add more tools or features

Share this project by:
- ✓ Committing to git (excluding .env)
- ✓ Sharing the GitHub link
- ✓ Including setup instructions (see QUICKSTART.md)

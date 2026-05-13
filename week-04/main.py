#!/usr/bin/env python3
"""
Week 4 Function Calling Assignment
Demonstrates multi-turn function calling with execute_sql and wget tools.
"""

import json
import os
import subprocess
import sys
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, APIError

# ============================================================================
# STEP 1: Project Setup & Configuration
# ============================================================================

def load_config() -> tuple[str, str, str]:
    """
    Load configuration from .env file.
    
    Returns:
        Tuple of (api_key, api_endpoint, model_name)
    
    Raises:
        ValueError: If any required environment variable is missing
    """
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    api_endpoint = os.getenv("OPENAI_API_ENDPOINT")
    model_name = os.getenv("MODEL")
    
    if not all([api_key, api_endpoint, model_name]):
        raise ValueError(
            "Missing required environment variables. "
            "Please ensure OPENAI_API_KEY, OPENAI_API_ENDPOINT, and MODEL are set in .env"
        )
    
    return api_key, api_endpoint, model_name


def initialize_client(api_key: str, api_endpoint: str) -> OpenAI:
    """
    Initialize OpenAI client with custom endpoint (Aliyun Qwen).
    
    Args:
        api_key: OpenAI API key
        api_endpoint: Custom API endpoint
    
    Returns:
        Configured OpenAI client
    """
    return OpenAI(api_key=api_key, base_url=api_endpoint)


# ============================================================================
# STEP 2: Define Function Calling Tools
# ============================================================================

def execute_sql(query: str) -> str:
    """
    Execute SQL query (simulated).
    
    In a real scenario, this would connect to a database.
    For this exercise, we simulate common SQL operations.
    
    Args:
        query: SQL query to execute
    
    Returns:
        Simulated query result
    """
    query_lower = query.lower().strip()
    
    # Simulated database schema
    simulated_users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ]
    
    # Simulated tables in database
    simulated_tables = ["users", "products", "orders"]
    
    # Handle table listing queries (SHOW TABLES, information_schema, sqlite_master)
    if "show tables" in query_lower:
        return json.dumps({
            "result": "rows",
            "data": [{"table_name": table} for table in simulated_tables]
        })
    
    if "information_schema" in query_lower and "table_name" in query_lower:
        return json.dumps({
            "result": "rows",
            "data": [{"table_name": table} for table in simulated_tables]
        })
    
    if "sqlite_master" in query_lower and "type='table'" in query_lower:
        return json.dumps({
            "result": "rows",
            "data": [{"name": table} for table in simulated_tables]
        })
    
    # Handle regular SELECT queries
    if "select" in query_lower:
        if "count" in query_lower:
            # Consistent count - matches the actual users
            return json.dumps({"result": "count", "value": len(simulated_users)})
        elif "users" in query_lower:
            return json.dumps({
                "result": "rows",
                "data": simulated_users
            })
        else:
            return json.dumps({"result": "rows", "data": []})
    
    elif "insert" in query_lower or "update" in query_lower or "delete" in query_lower:
        return json.dumps({"result": "success", "affected_rows": 1})
    
    elif "create table" in query_lower:
        return json.dumps({"result": "table_created", "status": "success"})
    
    else:
        return json.dumps({"result": "unknown", "error": "Unsupported query type"})


def wget_file(url: str, output_path: Optional[str] = None) -> str:
    """
    Download a file from URL using wget (with user confirmation).
    
    Args:
        url: URL to download
        output_path: Optional output file path
    
    Returns:
        Download result message
    """
    if not url.startswith(("http://", "https://")):
        return json.dumps({
            "result": "error",
            "message": f"Invalid URL: {url}"
        })
    
    # Request user confirmation before downloading
    print("\n" + "=" * 70)
    print(f"⚠️  DOWNLOAD REQUEST")
    print(f"URL: {url}")
    if output_path:
        print(f"Output: {output_path}")
    print("=" * 70)
    
    try:
        user_response = input("Do you want to proceed with this download? (yes/no): ").strip().lower()
    except EOFError:
        user_response = "no"
    
    if user_response not in ("yes", "y"):
        return json.dumps({
            "result": "cancelled",
            "message": "Download cancelled by user"
        })
    
    # Try multiple wget paths for cross-platform compatibility
    wget_paths = [
        "/opt/homebrew/bin/wget",  # macOS with Homebrew (Apple Silicon)
        "/usr/local/bin/wget",      # macOS with Homebrew (Intel)
        "wget"                      # Standard PATH
    ]
    
    wget_cmd = None
    for path in wget_paths:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                wget_cmd = path
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not wget_cmd:
        return json.dumps({
            "result": "error",
            "message": "wget command not found. Install it with: brew install wget"
        })
    
    # Simulate the download with wget
    try:
        output_arg = ["-O", output_path] if output_path else []
        cmd = [wget_cmd, "--quiet"] + output_arg + [url]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            filename = output_path or url.split('/')[-1]
            return json.dumps({
                "result": "success",
                "message": f"Downloaded successfully to {filename}",
                "url": url,
                "filename": filename
            })
        else:
            return json.dumps({
                "result": "error",
                "message": f"wget failed: {result.stderr}"
            })
    
    except subprocess.TimeoutExpired:
        return json.dumps({
            "result": "error",
            "message": "Download timed out after 30 seconds"
        })
    except Exception as e:
        return json.dumps({
            "result": "error",
            "message": f"Unexpected error: {str(e)}"
        })


# ============================================================================
# STEP 3: Tool Definitions for Function Calling
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Execute a SQL query against the database. Can SELECT, INSERT, UPDATE, or DELETE data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wget_file",
            "description": "Download a file from the internet using wget. Requires user confirmation before downloading.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to download from"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional output file path. If not provided, uses the URL filename."
                    }
                },
                "required": ["url"]
            }
        }
    }
]


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """
    Process a tool call and return the result.
    
    Args:
        tool_name: Name of the function to call
        tool_input: Arguments for the function
    
    Returns:
        JSON string with the result
    """
    if tool_name == "execute_sql":
        return execute_sql(tool_input.get("query", ""))
    elif tool_name == "wget_file":
        return wget_file(
            tool_input.get("url", ""),
            tool_input.get("output_path")
        )
    else:
        return json.dumps({
            "result": "error",
            "message": f"Unknown tool: {tool_name}"
        })


def convert_message_to_dict(message) -> dict:
    """
    Convert OpenAI message object to dict format compatible with Aliyun Qwen API.
    
    Args:
        message: OpenAI message object
    
    Returns:
        Dictionary representation of the message
    """
    msg_dict = {
        "role": message.role,
        "content": message.content or ""
    }
    return msg_dict


# ============================================================================
# STEP 4: Main Function Calling Loop (Steps 3-5)
# ============================================================================

def run_conversation(client: OpenAI, model: str) -> None:
    """
    Run a multi-turn conversation with function calling.
    
    Implements:
    - Step 3: Function calling with user prompts
    - Step 4: While loop for continuous interaction
    - Step 5: Error handling and proper cleanup
    
    Args:
        client: Initialized OpenAI client
        model: Model name to use
    """
    messages = []
    
    print("\n" + "=" * 70)
    print("Week 4 Function Calling Assistant")
    print("=" * 70)
    print("Commands you can try:")
    print("  - 'List all users from the database'")
    print("  - 'Download a file from https://www.example.com/file.txt'")
    print("  - 'How many rows are in the users table?'")
    print("  - 'quit' or 'exit' to end the conversation")
    print("=" * 70 + "\n")
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit"):
                print("Goodbye!")
                break
            
            # Add user message to conversation
            messages.append({"role": "user", "content": user_input})
            
            # Loop for handling tool calls
            while True:
                try:
                    # Make API call with function calling
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto"
                    )
                
                except APIError as e:
                    print(f"\n❌ API Error: {e}")
                    print("Please check your API key and endpoint configuration.")
                    # Remove the last user message that caused the error
                    if messages and messages[-1]["role"] == "user":
                        messages.pop()
                    break
                
                except Exception as e:
                    print(f"\n❌ Unexpected error: {e}")
                    if messages and messages[-1]["role"] == "user":
                        messages.pop()
                    break
                
                # Check the response
                finish_reason = response.choices[0].finish_reason
                
                # If no tool calls, print response and exit the loop
                if finish_reason == "stop":
                    assistant_message = response.choices[0].message.content
                    if assistant_message:
                        print(f"\nAssistant: {assistant_message}\n")
                    # Convert message object to dict for API compatibility
                    messages.append(convert_message_to_dict(response.choices[0].message))
                    break
                
                # If tool calls are needed, process them
                elif finish_reason == "tool_calls":
                    assistant_message = response.choices[0].message
                    # Convert message object to dict format for API compatibility
                    messages.append(convert_message_to_dict(assistant_message))
                    
                    # Process each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_input = json.loads(tool_call.function.arguments)
                        
                        print(f"\n🔧 Calling tool: {tool_name}")
                        print(f"   Arguments: {json.dumps(tool_input, indent=2)}")
                        
                        try:
                            tool_result = process_tool_call(tool_name, tool_input)
                            
                            # For Aliyun Qwen compatibility, format tool result as text
                            # Some APIs don't support the OpenAI tool_result format
                            result_text = f"Tool '{tool_name}' result:\n{tool_result}"
                            
                            # Add tool result to messages as a user message
                            messages.append({
                                "role": "user",
                                "content": result_text
                            })
                            
                            result_json = json.loads(tool_result)
                            print(f"   Result: {json.dumps(result_json, indent=2)}\n")
                        
                        except json.JSONDecodeError as e:
                            print(f"   ❌ Error parsing tool result: {e}\n")
                            messages.pop()  # Remove the assistant message
                            break
                        
                        except Exception as e:
                            print(f"   ❌ Tool execution error: {e}\n")
                            messages.pop()
                            break
                    else:
                        # All tool calls processed successfully, continue loop
                        continue
                    
                    # If there was an error, break out of tool loop
                    break
                
                else:
                    print(f"\nUnexpected finish reason: {finish_reason}\n")
                    break
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main() -> None:
    """Main entry point for the program."""
    try:
        # Load configuration
        print("Loading configuration...")
        api_key, api_endpoint, model_name = load_config()
        print(f"✓ Configuration loaded (Model: {model_name})")
        
        # Initialize client
        print("Initializing API client...")
        client = initialize_client(api_key, api_endpoint)
        print("✓ API client initialized")
        
        # Run conversation loop
        run_conversation(client, model_name)
    
    except ValueError as e:
        print(f"❌ Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ Fatal Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

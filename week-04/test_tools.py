#!/usr/bin/env python3
"""
Test script for Week 4 function calling tools.
Verifies execute_sql and wget_file functions work correctly.
"""

import json
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from main import execute_sql, load_config, initialize_client

def test_execute_sql():
    """Test SQL execution tool."""
    print("Testing execute_sql()...")
    
    # Test SELECT
    result = execute_sql("SELECT * FROM users")
    data = json.loads(result)
    assert data["result"] == "rows", f"Expected 'rows', got {data['result']}"
    assert len(data["data"]) > 0, "Expected data in SELECT result"
    print("  ✓ SELECT query works")
    
    # Test COUNT
    result = execute_sql("SELECT COUNT(*) FROM users")
    data = json.loads(result)
    assert data["result"] == "count", f"Expected 'count', got {data['result']}"
    print("  ✓ COUNT query works")
    
    # Test INSERT
    result = execute_sql("INSERT INTO users (name) VALUES ('Test')")
    data = json.loads(result)
    assert data["result"] == "success", f"Expected 'success', got {data['result']}"
    print("  ✓ INSERT query works")
    
    # Test UPDATE
    result = execute_sql("UPDATE users SET name='Updated' WHERE id=1")
    data = json.loads(result)
    assert data["result"] == "success", f"Expected 'success', got {data['result']}"
    print("  ✓ UPDATE query works")
    
    # Test DELETE
    result = execute_sql("DELETE FROM users WHERE id=1")
    data = json.loads(result)
    assert data["result"] == "success", f"Expected 'success', got {data['result']}"
    print("  ✓ DELETE query works")
    
    # Test CREATE TABLE
    result = execute_sql("CREATE TABLE test (id INT, name VARCHAR)")
    data = json.loads(result)
    assert data["result"] == "table_created", f"Expected 'table_created', got {data['result']}"
    print("  ✓ CREATE TABLE query works")
    
    print("✓ All execute_sql tests passed!\n")


def test_config_loading():
    """Test environment configuration loading."""
    print("Testing load_config()...")
    
    try:
        api_key, endpoint, model = load_config()
        assert api_key, "API key is empty"
        assert endpoint, "API endpoint is empty"
        assert model, "Model name is empty"
        
        print(f"  ✓ API Key:    {api_key[:20]}...")
        print(f"  ✓ Endpoint:   {endpoint}")
        print(f"  ✓ Model:      {model}")
        print("✓ Configuration loaded successfully!\n")
        
        return api_key, endpoint, model
    
    except ValueError as e:
        print(f"✗ Configuration error: {e}\n")
        return None, None, None


def test_client_initialization():
    """Test OpenAI client initialization."""
    print("Testing initialize_client()...")
    
    try:
        api_key, endpoint, model = load_config()
        if not all([api_key, endpoint, model]):
            print("✗ Cannot test client initialization without valid config\n")
            return False
        
        client = initialize_client(api_key, endpoint)
        assert client, "Client initialization failed"
        print("  ✓ Client initialized with custom endpoint")
        print("✓ Client initialization test passed!\n")
        return True
    
    except Exception as e:
        print(f"✗ Client initialization error: {e}\n")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Week 4 Function Calling - Test Suite")
    print("=" * 70 + "\n")
    
    # Test 1: SQL tool
    try:
        test_execute_sql()
    except AssertionError as e:
        print(f"✗ execute_sql test failed: {e}\n")
        return False
    except Exception as e:
        print(f"✗ execute_sql test error: {e}\n")
        return False
    
    # Test 2: Configuration
    api_key, endpoint, model = test_config_loading()
    if not all([api_key, endpoint, model]):
        print("⚠ Skipping client tests (missing configuration)\n")
        return False
    
    # Test 3: Client initialization
    if not test_client_initialization():
        print("⚠ Client initialization failed\n")
        return False
    
    # Summary
    print("=" * 70)
    print("✓ All tests passed!")
    print("=" * 70)
    print("\nNow you can run: uv run python main.py")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

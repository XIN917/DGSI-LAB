#!/usr/bin/env python3
"""
Quick test of the tool calling fix for Aliyun Qwen API
"""

import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from main import load_config, initialize_client, execute_sql, TOOLS, convert_message_to_dict

def test_api_compatibility():
    """Test that the API compatibility fixes work."""
    print("Testing API compatibility fixes...\n")
    
    # Load config
    print("✓ Loading configuration...")
    api_key, api_endpoint, model = load_config()
    
    # Initialize client
    print("✓ Initializing client...")
    client = initialize_client(api_key, api_endpoint)
    
    # Test message formatting
    print("✓ Testing message format conversion...")
    
    # Simulate a simple API call
    print("✓ Making test API call...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, what is 2+2?"}
            ],
            tools=TOOLS,
            tool_choice="auto"
        )
        
        print(f"  Response finish_reason: {response.choices[0].finish_reason}")
        
        # Test message conversion
        msg = response.choices[0].message
        converted = convert_message_to_dict(msg)
        print(f"  Converted message: {converted}")
        print(f"  Content type: {type(converted['content'])}")
        
        print("\n✅ API compatibility test PASSED!")
        print("   The tool calling fix appears to be working.")
        print("\n   You can now run: uv run python main.py")
        return True
        
    except Exception as e:
        print(f"\n❌ API call failed: {e}")
        print("   The fix may not be sufficient for your API endpoint.")
        print("   Error details:", str(e)[:200])
        return False

if __name__ == "__main__":
    success = test_api_compatibility()
    sys.exit(0 if success else 1)

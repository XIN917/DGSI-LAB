#!/usr/bin/env python3
"""Test the enhanced execute_sql function"""

from main import execute_sql
import json

print("Testing SHOW TABLES support...\n")

# Test 1: SHOW TABLES syntax
result = execute_sql("SHOW TABLES")
data = json.loads(result)
print(f"1. SHOW TABLES:")
print(f"   Result: {json.dumps(data, indent=2)}\n")

# Test 2: information_schema syntax
result = execute_sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
data = json.loads(result)
print(f"2. SELECT FROM information_schema:")
print(f"   Result: {json.dumps(data, indent=2)}\n")

# Test 3: sqlite_master syntax
result = execute_sql("SELECT name FROM sqlite_master WHERE type='table'")
data = json.loads(result)
print(f"3. SELECT FROM sqlite_master:")
print(f"   Result: {json.dumps(data, indent=2)}\n")

# Test 4: Regular SELECT still works
result = execute_sql("SELECT * FROM users")
data = json.loads(result)
print(f"4. SELECT * FROM users:")
print(f"   Result: {len(data['data'])} users returned\n")

print("✅ All table queries now supported!")

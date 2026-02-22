#!/usr/bin/env python3
"""测试 .env 文件加载"""
from pathlib import Path
from dotenv import load_dotenv
import os

# 测试路径解析
test_file = Path(__file__).resolve()
env_path = test_file.parent / '.env'

print(f"Script location: {test_file}")
print(f"Expected .env path: {env_path}")
print(f".env exists: {env_path.exists()}")

if env_path.exists():
    load_dotenv(env_path)
    print(f"\n✅ .env file loaded successfully!")
    print(f"\nEnvironment variables:")
    print(f"  GEE_USER_PATH: {os.getenv('GEE_USER_PATH', 'NOT SET')}")
    print(f"  API_PORT: {os.getenv('API_PORT', 'NOT SET')}")
    print(f"  FRONTEND_PORT: {os.getenv('FRONTEND_PORT', 'NOT SET')}")
else:
    print(f"\n❌ .env file not found at: {env_path}")

#!/usr/bin/env python3

try:
    from app.main import app

    print("✅ FastAPI app imported successfully!")
    print(f"App title: {app.title}")
    print(f"App version: {app.version}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback

    traceback.print_exc()

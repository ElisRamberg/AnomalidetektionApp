#!/usr/bin/env python3
"""
Test script for upload functionality.
Run this after starting the FastAPI server.
"""


from pathlib import Path

import requests

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_FILES = {"csv": "test_data/sample.csv", "json": "test_data/sample.json"}


def test_upload_file(file_path: str, file_type: str):
    """Test uploading a single file."""
    print(f"\n🧪 Testing {file_type.upper()} upload: {file_path}")

    if not Path(file_path).exists():
        print(f"❌ Test file not found: {file_path}")
        return None

    try:
        # Upload file
        with open(file_path, "rb") as f:
            files = {
                "file": (
                    Path(file_path).name,
                    f,
                    "text/csv" if file_type == "csv" else "application/json",
                )
            }
            data = {"auto_analyze": False}

            response = requests.post(f"{BASE_URL}/upload", files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   📁 File ID: {result['id']}")
            print(f"   📊 File size: {result['file_size']} bytes")
            print(f"   📅 Upload time: {result['upload_timestamp']}")
            print(f"   🏷️  Status: {result['status']}")
            return result["id"]
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the server running on http://localhost:8000?")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def test_get_upload_status(upload_id: str):
    """Test getting upload status."""
    print(f"\n🔍 Checking upload status for ID: {upload_id}")

    try:
        response = requests.get(f"{BASE_URL}/upload/{upload_id}/status")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status check successful!")
            print(f"   🏷️  Status: {result['status']}")
            print(f"   📁 Filename: {result['filename']}")
            if result.get("error_message"):
                print(f"   ⚠️  Error: {result['error_message']}")
        else:
            print(f"❌ Status check failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"❌ Error checking status: {e}")


def test_get_upload_history():
    """Test getting upload history."""
    print(f"\n📋 Getting upload history...")

    try:
        response = requests.get(f"{BASE_URL}/upload/history")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ History retrieved successfully!")
            print(f"   📊 Total uploads: {result['total']}")
            print(f"   📄 Current page: {result['page']}")

            if result["uploads"]:
                print(f"   📁 Recent uploads:")
                for upload in result["uploads"][:3]:  # Show first 3
                    print(f"      - {upload['original_filename']} ({upload['status']})")
        else:
            print(f"❌ History retrieval failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Error getting history: {e}")


def test_get_upload_stats():
    """Test getting upload statistics."""
    print(f"\n📈 Getting upload statistics...")

    try:
        response = requests.get(f"{BASE_URL}/upload/stats")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Statistics retrieved successfully!")
            print(f"   📊 Total uploads: {result['total_uploads']}")
            print(f"   ✅ Successful: {result['successful_uploads']}")
            print(f"   ❌ Failed: {result['failed_uploads']}")
            print(f"   ⏳ Processing: {result['processing_uploads']}")
            print(f"   💾 Total size: {result['total_size_bytes']} bytes")
        else:
            print(f"❌ Stats retrieval failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Error getting stats: {e}")


def main():
    """Run all tests."""
    print("🚀 Starting Upload API Tests")
    print("=" * 50)

    # Test server connectivity
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/")
        if response.status_code == 200:
            print("✅ Server is running!")
        else:
            print("❌ Server responded with error")
            return
    except:
        print("❌ Cannot connect to server. Please start it with:")
        print(
            "   cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        )
        return

    upload_ids = []

    # Test file uploads
    for file_type, file_path in TEST_FILES.items():
        upload_id = test_upload_file(file_path, file_type)
        if upload_id:
            upload_ids.append(upload_id)

    # Test status checks
    for upload_id in upload_ids:
        test_get_upload_status(upload_id)

    # Test history and stats
    test_get_upload_history()
    test_get_upload_stats()

    print("\n" + "=" * 50)
    print("🎉 Testing complete!")

    if upload_ids:
        print(f"\n💡 You can also test manually:")
        print(f"   - Open http://localhost:8000/docs in your browser")
        print(f"   - Try the interactive API documentation")
        print(f"   - Check uploaded files in the backend/uploads/ directory")


if __name__ == "__main__":
    main()

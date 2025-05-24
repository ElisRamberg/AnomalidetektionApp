"""Tests for upload API endpoints."""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from fastapi import status
import uuid

from app.models.upload import FileUpload


class TestUploadAPI:
    """Test cases for upload API endpoints."""

    @pytest.mark.asyncio
    async def test_upload_file_csv_success(self, client: AsyncClient, sample_csv_content: bytes):
        """Test successful CSV file upload."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(sample_csv_content)
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, 'rb') as f:
                response = await client.post(
                    "/api/v1/upload",
                    files={"file": ("test.csv", f, "text/csv")},
                    data={"auto_analyze": "false"}
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "id" in data
            assert data["original_filename"] == "test.csv"
            assert data["file_type"] == "csv"
            assert data["status"] == "uploaded"
        finally:
            os.unlink(tmp_file_path)

    @pytest.mark.asyncio
    async def test_upload_file_json_success(self, client: AsyncClient, sample_json_content: bytes):
        """Test successful JSON file upload."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_file:
            tmp_file.write(sample_json_content)
            tmp_file_path = tmp_file.name

        try:
            with open(tmp_file_path, 'rb') as f:
                response = await client.post(
                    "/api/v1/upload",
                    files={"file": ("test.json", f, "application/json")},
                    data={"auto_analyze": "true", "strategy_id": str(uuid.uuid4())}
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["file_type"] == "json"
            assert data["metadata"]["auto_analyze"] is True
        finally:
            os.unlink(tmp_file_path)

    @pytest.mark.asyncio
    async def test_upload_file_invalid_type(self, client: AsyncClient):
        """Test upload with unsupported file type."""
        content = b"This is not a valid file"
        
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("test.txt", content, "text/plain")},
            data={"auto_analyze": "false"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, client: AsyncClient):
        """Test upload with file that's too large."""
        # Create a large file content (simulate large file)
        large_content = b"a" * (100 * 1024 * 1024)  # 100MB
        
        with patch("app.utils.file_validators.FileValidator.validate_file_size") as mock_validate:
            mock_validate.side_effect = Exception("File too large")
            
            response = await client.post(
                "/api/v1/upload",
                files={"file": ("large.csv", large_content, "text/csv")},
                data={"auto_analyze": "false"}
            )

        assert response.status_code == status.HTTP_500_OK

    @pytest.mark.asyncio
    async def test_upload_file_invalid_structure(self, client: AsyncClient):
        """Test upload with invalid file structure."""
        invalid_content = b"invalid,csv,structure\nno,proper,headers"
        
        with patch("app.services.file_processor.FileProcessorService.validate_file") as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Invalid CSV structure"}
            
            response = await client.post(
                "/api/v1/upload",
                files={"file": ("invalid.csv", invalid_content, "text/csv")},
                data={"auto_analyze": "false"}
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid file structure" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_upload_status_success(self, client: AsyncClient, db_session, sample_upload):
        """Test getting upload status."""
        response = await client.get(f"/api/v1/upload/{sample_upload.id}/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_upload.id)
        assert data["status"] == sample_upload.status

    @pytest.mark.asyncio
    async def test_get_upload_status_not_found(self, client: AsyncClient):
        """Test getting status for non-existent upload."""
        non_existent_id = uuid.uuid4()
        response = await client.get(f"/api/v1/upload/{non_existent_id}/status")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_upload_history_success(self, client: AsyncClient, db_session, sample_uploads):
        """Test getting upload history with pagination."""
        response = await client.get("/api/v1/upload/history?page=1&per_page=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "uploads" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "has_next" in data
        assert "has_prev" in data
        assert len(data["uploads"]) <= 10

    @pytest.mark.asyncio
    async def test_get_upload_history_with_status_filter(self, client: AsyncClient, sample_uploads):
        """Test getting upload history with status filter."""
        response = await client.get("/api/v1/upload/history?status=processed&page=1&per_page=5")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(upload["status"] == "processed" for upload in data["uploads"])

    @pytest.mark.asyncio
    async def test_get_upload_history_pagination_limits(self, client: AsyncClient):
        """Test upload history pagination limits."""
        # Test maximum per_page limit
        response = await client.get("/api/v1/upload/history?per_page=150")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["per_page"] == 100  # Should be capped at 100

    @pytest.mark.asyncio
    async def test_get_upload_stats_success(self, client: AsyncClient, sample_uploads):
        """Test getting upload statistics."""
        response = await client.get("/api/v1/upload/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_uploads" in data
        assert "successful_uploads" in data
        assert "failed_uploads" in data
        assert "processing_uploads" in data
        assert "total_size_bytes" in data
        assert "total_transactions_processed" in data
        assert isinstance(data["total_uploads"], int)
        assert isinstance(data["total_size_bytes"], int)

    @pytest.mark.asyncio
    async def test_delete_upload_success(self, client: AsyncClient, db_session, sample_upload):
        """Test successful upload deletion."""
        # Create a temporary file to simulate the uploaded file
        upload_dir = "/tmp/test_uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, sample_upload.filename)
        
        with open(file_path, 'w') as f:
            f.write("test content")

        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.upload_dir = upload_dir
            
            response = await client.delete(f"/api/v1/upload/{sample_upload.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Upload deleted successfully"
        
        # Verify file was deleted
        assert not os.path.exists(file_path)
        
        # Cleanup
        if os.path.exists(upload_dir):
            os.rmdir(upload_dir)

    @pytest.mark.asyncio
    async def test_delete_upload_not_found(self, client: AsyncClient):
        """Test deleting non-existent upload."""
        non_existent_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/upload/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_upload_with_database_error(self, client: AsyncClient, sample_csv_content):
        """Test upload handling when database operation fails."""
        with patch("app.database.get_async_db") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")
            
            response = await client.post(
                "/api/v1/upload",
                files={"file": ("test.csv", sample_csv_content, "text/csv")},
                data={"auto_analyze": "false"}
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_upload_file_validation_edge_cases(self, client: AsyncClient):
        """Test various edge cases in file validation."""
        # Empty file
        empty_content = b""
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("empty.csv", empty_content, "text/csv")},
            data={"auto_analyze": "false"}
        )
        # Should handle empty files gracefully
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]

        # File with special characters in name
        special_content = b"amount,timestamp,account_id\n100,2023-01-01,ACC001"
        response = await client.post(
            "/api/v1/upload",
            files={"file": ("test-file_name.csv", special_content, "text/csv")},
            data={"auto_analyze": "false"}
        )
        # Should handle special characters in filename
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, client: AsyncClient, sample_csv_content):
        """Test handling of concurrent uploads."""
        import asyncio
        
        async def upload_file(filename):
            return await client.post(
                "/api/v1/upload",
                files={"file": (filename, sample_csv_content, "text/csv")},
                data={"auto_analyze": "false"}
            )

        # Simulate multiple concurrent uploads
        tasks = [upload_file(f"test_{i}.csv") for i in range(3)]
        responses = await asyncio.gather(*tasks)

        # All uploads should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

        # Each should have unique IDs
        upload_ids = [response.json()["id"] for response in responses]
        assert len(set(upload_ids)) == len(upload_ids)  # All unique 
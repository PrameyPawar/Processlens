"""
Application settings and constants for ProcessLens.
"""

from typing import List

class Settings:
    PROJECT_NAME: str = "ProcessLens API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Ingestion constraints
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: List[str] = [".csv"]
    ALLOWED_MIME_TYPES: List[str] = [
        "text/csv",
        "application/vnd.ms-excel",
        "text/csv; charset=utf-8",
        "text/plain",
        "application/octet-stream"
    ]
    
    # Canonical event log schema standards
    CANONICAL_REQUIRED_COLUMNS: List[str] = ["case_id", "activity", "timestamp"]

settings = Settings()

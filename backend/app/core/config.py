"""
Application settings and constants for ProcessLens.
"""

import os
from typing import List, Optional

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

    # LLM Provider Configuration
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY", None)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
settings = Settings()

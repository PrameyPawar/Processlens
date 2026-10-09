"""
FastAPI application entrypoint for ProcessLens.
Provides health check and CSV ingestion endpoints.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.ingestion import DataQualityReport
from app.services.validator import validate_csv_content

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint to verify backend service readiness."""
    return {
        "status": "ok",
        "service": "processlens-backend",
        "version": settings.VERSION
    }

@app.post(f"{settings.API_V1_STR}/ingestion/upload", response_model=DataQualityReport, status_code=status.HTTP_200_OK)
async def upload_csv_file(file: UploadFile = File(...)):
    """
    Ingests a CSV event log file, validates schema and data quality, 
    and returns a structured DataQualityReport.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    # File extension check
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Only CSV files ({', '.join(settings.ALLOWED_EXTENSIONS)}) are allowed."
        )

    content = await file.read()

    # File size check
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        report = validate_csv_content(content, file.filename)
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the file: {str(e)}"
        )

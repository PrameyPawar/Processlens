"""
FastAPI application entrypoint for ProcessLens.
Provides health check and CSV ingestion endpoints.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.ingestion import DataQualityReport
from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import ProcessAnalyticsResult
from app.schemas.detection import ProblemDetectionResult
from app.schemas.opportunity import OpportunityDetectionResult
from app.services.validator import validate_csv_content
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import detect_process_problems
from app.services.opportunity import detect_improvement_opportunities

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

@app.post(f"{settings.API_V1_STR}/process/reconstruct", response_model=ProcessReconstructionResult, status_code=status.HTTP_200_OK)
async def reconstruct_process_endpoint(file: UploadFile = File(...)):
    """
    Reconstructs chronological case traces, activity sequences, and process variants
    from an uploaded CSV event log.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Only CSV files ({', '.join(settings.ALLOWED_EXTENSIONS)}) are allowed."
        )

    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        result = reconstruct_process_from_csv(content, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while reconstructing the process: {str(e)}"
        )

@app.post(f"{settings.API_V1_STR}/analytics/process", response_model=ProcessAnalyticsResult, status_code=status.HTTP_200_OK)
async def analyze_process_endpoint(file: UploadFile = File(...)):
    """
    Reconstructs the process and computes deterministic process metrics
    including cycle times, activity frequencies, rework indicators, and transitions.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Only CSV files ({', '.join(settings.ALLOWED_EXTENSIONS)}) are allowed."
        )

    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        reconstruction = reconstruct_process_from_csv(content, file.filename)
        analytics_result = calculate_process_analytics(reconstruction)
        return analytics_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while analyzing the process: {str(e)}"
        )

@app.post(f"{settings.API_V1_STR}/problems/detect", response_model=ProblemDetectionResult, status_code=status.HTTP_200_OK)
async def detect_problems_endpoint(file: UploadFile = File(...)):
    """
    Reconstructs the process, calculates analytics, and executes deterministic
    problem and bottleneck detection including accounting reconciliation integrity checks.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Only CSV files ({', '.join(settings.ALLOWED_EXTENSIONS)}) are allowed."
        )

    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        reconstruction = reconstruct_process_from_csv(content, file.filename)
        analytics_result = calculate_process_analytics(reconstruction)
        detection_result = detect_process_problems(reconstruction, analytics_result)
        return detection_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while detecting process problems: {str(e)}"
        )

@app.post(f"{settings.API_V1_STR}/opportunities/detect", response_model=OpportunityDetectionResult, status_code=status.HTTP_200_OK)
async def detect_opportunities_endpoint(file: UploadFile = File(...)):
    """
    Reconstructs the process, calculates metrics, detects operational problems, and
    derives deterministic, evidence-backed improvement and automation opportunity candidates.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Only CSV files ({', '.join(settings.ALLOWED_EXTENSIONS)}) are allowed."
        )

    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        reconstruction = reconstruct_process_from_csv(content, file.filename)
        analytics_result = calculate_process_analytics(reconstruction)
        detection_result = detect_process_problems(reconstruction, analytics_result)
        opportunity_result = detect_improvement_opportunities(reconstruction, analytics_result, detection_result)
        return opportunity_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while detecting opportunities: {str(e)}"
        )


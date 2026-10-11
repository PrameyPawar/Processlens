"""
FastAPI application entrypoint for ProcessLens.
Provides health check and CSV ingestion endpoints.
"""

from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.ingestion import DataQualityReport
from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import ProcessAnalyticsResult
from app.schemas.detection import ProblemDetectionResult
from app.schemas.opportunity import OpportunityDetectionResult
from app.schemas.readiness import ReadinessAssessmentResponse
from app.schemas.economics import EconomicsEvaluationResponse
from app.schemas.prioritisation import PrioritisationResponse
from app.services.validator import validate_csv_content
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import detect_process_problems
from app.services.opportunity import detect_improvement_opportunities
from app.services.readiness import parse_domain_assessments_json, assess_opportunities_readiness
from app.services.economics import parse_economic_inputs_json, evaluate_opportunities_economics
from app.services.prioritisation import parse_prioritisation_weights_json, prioritise_opportunities_portfolio

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


@app.post(f"{settings.API_V1_STR}/readiness/assess", response_model=ReadinessAssessmentResponse, status_code=status.HTTP_200_OK)
async def assess_readiness_endpoint(
    file: UploadFile = File(...),
    domain_assessments: Optional[str] = Form(None),
):
    """
    Reconstructs the process, computes analytics, detects problems and opportunities,
    and deterministically assesses automation readiness across six dimensions.
    Reuses existing pipeline services with zero logic duplication.
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

    # Validate and parse domain assessments JSON if provided
    try:
        parsed_domain = parse_domain_assessments_json(domain_assessments)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        reconstruction = reconstruct_process_from_csv(content, file.filename)
        analytics_result = calculate_process_analytics(reconstruction)
        detection_result = detect_process_problems(reconstruction, analytics_result)
        opportunity_result = detect_improvement_opportunities(reconstruction, analytics_result, detection_result)
        readiness_result = assess_opportunities_readiness(opportunity_result, parsed_domain, file.filename)
        return readiness_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while assessing automation readiness: {str(e)}"
        )


@app.post(f"{settings.API_V1_STR}/economics/evaluate", response_model=EconomicsEvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_economics_endpoint(
    file: UploadFile = File(...),
    economic_inputs: Optional[str] = Form(None),
    domain_assessments: Optional[str] = Form(None),
):
    """
    Executes the end-to-end ProcessLens analysis pipeline and evaluates business-impact
    and financial economics across candidate improvement and automation opportunities.
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

    # Validate and parse economic inputs JSON if provided
    try:
        parsed_economics = parse_economic_inputs_json(economic_inputs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Validate and parse domain assessments JSON if provided
    try:
        parsed_domain = parse_domain_assessments_json(domain_assessments)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        reconstruction = reconstruct_process_from_csv(content, file.filename)
        analytics_result = calculate_process_analytics(reconstruction)
        detection_result = detect_process_problems(reconstruction, analytics_result)
        opportunity_result = detect_improvement_opportunities(reconstruction, analytics_result, detection_result)
        readiness_result = assess_opportunities_readiness(opportunity_result, parsed_domain, file.filename)
        economics_result = evaluate_opportunities_economics(
            opportunity_result=opportunity_result,
            readiness_result=readiness_result,
            reconstruction=reconstruction,
            economic_inputs=parsed_economics,
            filename=file.filename,
        )
        return economics_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while evaluating economics: {str(e)}"
        )


@app.post(f"{settings.API_V1_STR}/prioritisation/rank", response_model=PrioritisationResponse, status_code=status.HTTP_200_OK)
async def rank_prioritisation_endpoint(
    file: UploadFile = File(...),
    prioritisation_weights: Optional[str] = Form(None),
    economic_inputs: Optional[str] = Form(None),
    domain_assessments: Optional[str] = Form(None),
):
    """
    Executes the end-to-end ProcessLens analysis pipeline (Reconstruction -> Analytics ->
    Problems -> Opportunities -> Readiness -> Economics -> Prioritisation) and produces a
    defensible, deterministic portfolio action roadmap.
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

    # Validate and parse prioritisation weights JSON if provided
    try:
        parsed_weights = parse_prioritisation_weights_json(prioritisation_weights)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Validate and parse economic inputs JSON if provided
    try:
        parsed_economics = parse_economic_inputs_json(economic_inputs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Validate and parse domain assessments JSON if provided
    try:
        parsed_domain = parse_domain_assessments_json(domain_assessments)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        reconstruction = reconstruct_process_from_csv(content, file.filename)
        analytics_result = calculate_process_analytics(reconstruction)
        detection_result = detect_process_problems(reconstruction, analytics_result)
        opportunity_result = detect_improvement_opportunities(reconstruction, analytics_result, detection_result)
        readiness_result = assess_opportunities_readiness(opportunity_result, parsed_domain, file.filename)
        economics_result = evaluate_opportunities_economics(
            opportunity_result=opportunity_result,
            readiness_result=readiness_result,
            reconstruction=reconstruction,
            economic_inputs=parsed_economics,
            filename=file.filename,
        )
        prioritisation_result = prioritise_opportunities_portfolio(
            economics_response=economics_result,
            opportunity_result=opportunity_result,
            readiness_result=readiness_result,
            reconstruction=reconstruction,
            weights=parsed_weights,
            filename=file.filename,
        )
        return prioritisation_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while prioritizing opportunities: {str(e)}"
        )

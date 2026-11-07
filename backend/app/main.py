"""
FastAPI application entrypoint for ProcessLens.
Provides health check and CSV ingestion endpoints.
"""

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from app.core.dependencies import require_analysis_user
from app.core.config import settings
from app.schemas.ingestion import DataQualityReport
from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import ProcessAnalyticsResult
from app.schemas.detection import ProblemDetectionResult
from app.schemas.opportunity import OpportunityDetectionResult
from app.schemas.readiness import ReadinessAssessmentResponse
from app.schemas.economics import EconomicsEvaluationResponse
from app.schemas.prioritisation import PrioritisationResponse
from app.schemas.evidence import EvidenceAuditResponse
from app.schemas.explanation import ExplanationResponse
from app.services.validator import validate_csv_content
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import detect_process_problems
from app.services.opportunity import detect_improvement_opportunities
from app.services.readiness import parse_domain_assessments_json, assess_opportunities_readiness
from app.services.economics import parse_economic_inputs_json, evaluate_opportunities_economics
from app.services.prioritisation import parse_prioritisation_weights_json, prioritise_opportunities_portfolio
from app.services.evidence import generate_evidence_audit_response
from app.services.explanation_pipeline import run_explanation_pipeline
from app.services.llm_provider import BaseLLMProvider, OpenAICompatibleProvider, LLMConfigurationError
from app.api.v1.auth import router as auth_router
from app.api.v1.dev import router as dev_router
from app.api.v1.customer import router as customer_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    RequestBodyLimitMiddleware,
    max_body_size=settings.MAX_FILE_SIZE_BYTES + 256 * 1024,
)

# Configure CORS for allowed origins
cors_origins = settings.CORS_ORIGINS
allow_all_origins = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def _read_upload_limited(file: UploadFile) -> bytes:
    """Read at most the configured upload limit plus one byte."""
    content = await file.read(settings.MAX_FILE_SIZE_BYTES + 1)
    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )
    return content


# Register authentication, customer workspace, and developer diagnostic routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(dev_router, prefix=settings.API_V1_STR)
app.include_router(customer_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def validate_startup_configuration():
    """Verify security requirements and environment settings at application boot."""
    settings.validate_configuration()


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint to verify backend service readiness."""
    return {
        "status": "ok",
        "service": "processlens-backend",
        "version": settings.VERSION
    }

@app.post(f"{settings.API_V1_STR}/ingestion/upload", response_model=DataQualityReport, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )

@app.post(f"{settings.API_V1_STR}/process/reconstruct", response_model=ProcessReconstructionResult, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )

@app.post(f"{settings.API_V1_STR}/analytics/process", response_model=ProcessAnalyticsResult, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )

@app.post(f"{settings.API_V1_STR}/problems/detect", response_model=ProblemDetectionResult, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )

@app.post(f"{settings.API_V1_STR}/opportunities/detect", response_model=OpportunityDetectionResult, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )


@app.post(f"{settings.API_V1_STR}/readiness/assess", response_model=ReadinessAssessmentResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )


@app.post(f"{settings.API_V1_STR}/economics/evaluate", response_model=EconomicsEvaluationResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )


@app.post(f"{settings.API_V1_STR}/prioritisation/rank", response_model=PrioritisationResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
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

    content = await _read_upload_limited(file)


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
            detail="An internal error occurred while processing this request."
        )


@app.post(f"{settings.API_V1_STR}/evidence/audit", response_model=EvidenceAuditResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
async def audit_evidence_endpoint(
    file: UploadFile = File(...),
    prioritisation_weights: Optional[str] = Form(None),
    economic_inputs: Optional[str] = Form(None),
    domain_assessments: Optional[str] = Form(None),
    opportunity_id: Optional[str] = Form(None),
):
    """
    Executes the end-to-end ProcessLens analysis pipeline and produces an auditable
    evidence dossier linking raw operational records, quantitative derivations, financial
    assumptions, readiness assessments, and portfolio prioritisation decisions.
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

    content = await _read_upload_limited(file)


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
        evidence_result = generate_evidence_audit_response(
            content_bytes=content,
            filename=file.filename,
            reconstruction=reconstruction,
            analytics=analytics_result,
            detection=detection_result,
            opportunity_result=opportunity_result,
            readiness_result=readiness_result,
            economics_result=economics_result,
            prioritisation_result=prioritisation_result,
            opportunity_id_filter=opportunity_id,
            weights_dict=parsed_weights.model_dump() if parsed_weights else None,
        )
        return evidence_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing this request."
        )


def get_llm_provider() -> Optional[BaseLLMProvider]:
    """
    FastAPI dependency resolving the configured LLM provider adapter.
    Returns None if provider credentials or settings are not configured.
    """
    try:
        return OpenAICompatibleProvider()
    except LLMConfigurationError:
        return None


@app.post(f"{settings.API_V1_STR}/explanation/generate", response_model=ExplanationResponse, status_code=status.HTTP_200_OK, dependencies=[Depends(require_analysis_user)])
async def generate_explanations_endpoint(
    file: UploadFile = File(...),
    enable_llm: bool = Form(False),
    prioritisation_weights: Optional[str] = Form(None),
    economic_inputs: Optional[str] = Form(None),
    domain_assessments: Optional[str] = Form(None),
    opportunity_id: Optional[str] = Form(None),
    provider: Optional[BaseLLMProvider] = Depends(get_llm_provider),
):
    """
    Executes the end-to-end ProcessLens analysis pipeline and generates executive
    explanations for prioritized opportunities.

    If enable_llm=True and provider is configured, generates LLM-augmented explanations
    and deterministically verifies grounding against Phase 9 evidence dossiers.
    If grounding fails, LLM call errors out, or provider is unconfigured, seamlessly
    returns deterministic template explanations with FALLBACK_APPLIED and structured reasons.
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

    content = await _read_upload_limited(file)


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
        evidence_result = generate_evidence_audit_response(
            content_bytes=content,
            filename=file.filename,
            reconstruction=reconstruction,
            analytics=analytics_result,
            detection=detection_result,
            opportunity_result=opportunity_result,
            readiness_result=readiness_result,
            economics_result=economics_result,
            prioritisation_result=prioritisation_result,
            opportunity_id_filter=opportunity_id,
            weights_dict=parsed_weights.model_dump() if parsed_weights else None,
        )

        return run_explanation_pipeline(
            audit_response=evidence_result,
            enable_llm=enable_llm,
            provider=provider,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing this request."
        )


# In a container deployment, serve the compiled SPA from this same origin as
# the API. This keeps browser session behavior predictable and supports
# client-side routes such as /login and /dev/dashboard on page refresh.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/{frontend_path:path}", include_in_schema=False)
def serve_frontend(frontend_path: str):
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontend assets are not installed.")

    if frontend_path == "" or frontend_path in {"login", "landing", "home", "dev/login", "dev/dashboard"}:
        return FileResponse(index_file)

    # Keep unknown API and health paths as real 404s instead of returning the SPA.
    if frontend_path in {"api", "health", "docs", "redoc"} or frontend_path.startswith(("api/", "health/", "docs/", "redoc/")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    dist_root = FRONTEND_DIST.resolve()
    candidate = (FRONTEND_DIST / frontend_path).resolve()
    try:
        candidate.relative_to(dist_root)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    if candidate.is_file():
        return FileResponse(candidate)
    # React owns client-side routes; return the SPA entrypoint for direct links.
    return FileResponse(index_file)

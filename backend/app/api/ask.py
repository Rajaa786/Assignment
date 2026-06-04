"""Natural-language Q&A endpoint.

Rate-limited (it calls a paid model and runs generated SQL) and intentionally thin: it
hands the question to the service, which guards and executes the SQL. Failures come back
as a generic message — the raw model output is never exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.api.dependencies import get_qa_service
from app.core.rate_limit import LLM_RATE_LIMIT, limiter
from app.schemas.qa import AskRequest, QueryAnswer
from app.services.qa_service import QaService

router = APIRouter(tags=["qa"])


@router.post("/ask", response_model=QueryAnswer, summary="Ask a question about pay")
@limiter.limit(LLM_RATE_LIMIT)
def ask(
    request: Request,
    payload: AskRequest,
    service: QaService = Depends(get_qa_service),
) -> QueryAnswer:
    """Answer a plain-English question about how the organization pays people."""
    return service.respond_to_natural_language_query(payload.question)

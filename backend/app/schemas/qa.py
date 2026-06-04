"""Transport schemas for the natural-language Q&A endpoint."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class AskRequest(BaseModel):
    """A natural-language question about how the organization pays people."""

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class QueryAnswer(BaseModel):
    """The answer to a question: the (guarded) SQL that ran and its result rows."""

    question: str
    sql: str = Field(description="The validated SQL that was executed.")
    columns: list[str] = Field(description="Result column names, in order.")
    rows: list[dict[str, object]] = Field(description="Result rows as JSON-safe objects.")
    row_count: int
    truncated: bool = Field(description="True if results were capped at the row limit.")

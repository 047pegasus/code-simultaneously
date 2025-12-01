# app/routers/autocomplete.py
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter()


class AutocompleteRequest(BaseModel):
    code: str
    cursor_position: int = Field(alias="cursorPosition")
    language: str = "python"

    class Config:
        allow_population_by_field_name = True


class AutocompleteResponse(BaseModel):
    suggestions: List[str]


@router.post("/autocomplete", response_model=AutocompleteResponse)
async def get_autocomplete(request: AutocompleteRequest):
    """
    Mocked autocomplete endpoint.

    Accepts the current code and cursor position and returns simple,
    rule-based suggestions.
    """
    current_line = request.code[: request.cursor_position].split("\n")[-1]
    stripped = current_line.strip()

    if stripped.endswith("."):
        suggestions = ["split()", "strip()", "replace()", "find()"]
    elif stripped.endswith("import "):
        suggestions = ["os", "sys", "json", "typing"]
    elif stripped.startswith("def "):
        suggestions = ["def function_name():", "def main():", "def handler(request):"]
    else:
        suggestions = ["def ", "for ", "if ", "while ", "class ", "import "]

    return AutocompleteResponse(suggestions=suggestions[:5])
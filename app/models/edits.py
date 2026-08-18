from pydantic import BaseModel, Field

class CodeEdit(BaseModel):
    file: str = Field(description="Repository-relative file path.")
    old: str = Field(description="Exact existing text to replace.")
    new: str = Field(description="Replacement text.")
    reason: str = Field(description="Why this edit is required.")

class CodeEditPlan(BaseModel):
    edits: list[CodeEdit]

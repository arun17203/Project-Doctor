from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

GITHUB_URL_REGEX = re.compile(
    r"^https?://(www\.)?github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?(\.git)?$"
)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Name of the software project")
    description: Optional[str] = Field(None, max_length=1000, description="Brief description of the project")
    source_type: Literal["zip", "github"] = Field(..., description="Project source type: zip or github")
    source_url: Optional[str] = Field(None, description="Public GitHub repository URL")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        return v

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if v and not GITHUB_URL_REGEX.match(v):
                raise ValueError("Invalid GitHub repository URL format. Example: https://github.com/owner/repo")
        return v


class GitHubImportRequest(BaseModel):
    github_url: str = Field(..., description="Public GitHub repository URL")

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip()
        if not GITHUB_URL_REGEX.match(v):
            raise ValueError("Invalid GitHub repository URL format. Example: https://github.com/owner/repo")
        return v


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    original_filename: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

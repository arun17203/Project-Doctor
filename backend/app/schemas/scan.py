from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict


class DiscoveredFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_path: str
    file_name: str
    extension: str
    language: str
    category: str
    size_bytes: int
    total_lines: int
    code_lines: int
    blank_lines: int
    comment_lines: int
    is_binary: bool
    is_test: bool
    is_config: bool
    is_doc: bool
    is_skipped: bool
    created_at: datetime


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    total_files: int
    total_directories: int
    total_lines: int
    total_code_lines: int
    total_blank_lines: int
    total_comment_lines: int
    test_files_count: int
    config_files_count: int
    doc_files_count: int
    languages_summary: Dict[str, Any]
    categories_summary: Dict[str, int]
    directory_tree: Dict[str, Any]
    status: str
    scanned_at: datetime


class ScanStatisticsResponse(BaseModel):
    project_id: str
    total_files: int
    total_directories: int
    total_lines: int
    total_code_lines: int
    total_blank_lines: int
    total_comment_lines: int
    test_files_count: int
    config_files_count: int
    doc_files_count: int
    languages: Dict[str, Any]
    categories: Dict[str, int]
    scanned_at: datetime

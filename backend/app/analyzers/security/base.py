from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Any


@dataclass
class SecurityFinding:
    issue_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence: str  # HIGH, MEDIUM, LOW
    file_path: str
    line_number: int
    message: str
    description: str
    category: str = "security"
    end_line: Optional[int] = None
    symbol_name: Optional[str] = None
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    rule_id: Optional[str] = None


class BaseSecurityRule(ABC):
    rule_id: str = "SEC-GENERIC-001"
    category: str = "security"
    cwe_id: str = "CWE-699"
    owasp_category: str = "A00:2021-General"

    @abstractmethod
    def run(
        self,
        file_path: str,
        content: str,
        ext: str,
        ast_tree: Optional[Any] = None,
    ) -> List[SecurityFinding]:
        """Analyze file content statically and return any detected security findings."""
        pass

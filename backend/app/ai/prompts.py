from typing import Dict, Any, Optional

SYSTEM_INSTRUCTION = """You are an expert software diagnostic engine and AI problem explainer for Project Doctor, an automated code health platform.

CRITICAL OPERATIONAL RULES:
1. You are explaining an existing, verified static-analysis finding detected by deterministic analyzers.
2. You must NEVER invent issues, vulnerabilities, files, or CVEs not present in the provided deterministic evidence.
3. You must NEVER claim to have executed, compiled, or run the user's code. This is static analysis only.
4. You must distinguish verified findings from potential risks using precise, cautious language (e.g. "The static analyzer detected a pattern consistent with SQL injection; review if the parameter is derived from untrusted input").
5. You must respect the deterministic analyzer severity as authoritative. You may recommend remediation urgency, but you must not claim the analyzer was incorrect.
6. For security findings, NEVER reveal, repeat, or unmask any secrets, passwords, or credentials. Always explain the architectural risk and recommend environment variable / secrets-management patterns.
7. For code quality findings, explain what the metric means, why it impairs maintainability or testing, and propose concrete refactoring techniques without rewriting the entire file.
8. For dependencies, refer exclusively to the provided manifest and Google OSV advisories. Do not fabricate CVE IDs.
9. For architecture circular dependencies, explain the topological cycle and recommend dependency inversion, interface abstraction, or module decomposition.
10. Return strictly valid JSON adhering to the requested schema.
"""


def build_explanation_prompt(
    category: str,
    issue_type: str,
    severity: str,
    file_path: Optional[str] = None,
    line_number: Optional[int] = None,
    symbol_name: Optional[str] = None,
    deterministic_message: Optional[str] = None,
    deterministic_description: Optional[str] = None,
    measured_metric: Optional[Any] = None,
    evidence: Optional[str] = None,
    source_snippet: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Builds a structured prompt providing deterministic evidence for Gemini."""

    lines = [
        "Please analyze and explain the following static-analysis finding:",
        f"- Diagnostic Category: {category.upper()}",
        f"- Finding Type: {issue_type}",
        f"- Analyzer Severity: {severity.upper()} (Authoritative)",
    ]

    if file_path:
        loc = file_path
        if line_number:
            loc += f":{line_number}"
        lines.append(f"- Location: {loc}")

    if symbol_name:
        lines.append(f"- Targeted Symbol / Function: {symbol_name}")

    if measured_metric is not None:
        lines.append(f"- Measured Telemetry / Metric: {measured_metric}")

    if deterministic_message:
        lines.append(f"- Analyzer Summary: {deterministic_message}")

    if deterministic_description:
        lines.append(f"- Analyzer Finding Details: {deterministic_description}")

    if evidence:
        lines.append(f"- Analyzer Masked Evidence: {evidence}")

    if extra_context:
        for k, v in extra_context.items():
            if v:
                lines.append(f"- {k.replace('_', ' ').title()}: {v}")

    if source_snippet:
        lines.append("\nRelevant Source Code Context (Read-Only Static Snippet):")
        lines.append("```")
        lines.append(source_snippet)
        lines.append("```")

    lines.append(
        "\nProvide your explanation in structured JSON conforming to the requested schema:\n"
        "- summary\n"
        "- why_it_matters\n"
        "- potential_impact\n"
        "- recommendation\n"
        "- priority\n"
        "- developer_action"
    )

    return "\n".join(lines)


QA_SYSTEM_INSTRUCTION = """You are a grounded Codebase Assistant for Project Doctor, an automated software health & diagnostic platform.
Your mission is to answer questions about the user's imported repository using ONLY the supplied repository evidence, static analysis findings, dependency advisories, architecture relationships, and code snippets.

CRITICAL OPERATIONAL RULES:
1. GROUNDING & EVIDENCE:
   - Answer ONLY using the supplied repository evidence (scan metadata, code snippets, static findings, dependency reports, architecture edges, and health scores).
   - If the provided evidence is not sufficient to support an answer, say explicitly: "I couldn't find enough evidence in this codebase to answer that."
   - Do NOT guess, fabricate, or invent files, functions, packages, CVEs, or relationships.
2. CITATIONS:
   - Every factual codebase claim should cite the specific file (and line numbers if known) from the retrieved evidence.
   - You must only cite files that are actually present in the provided evidence.
   - Do NOT invent file paths or line numbers.
3. FACTS VS INFERENCES:
   - Clearly distinguish between FACT (directly supported by code/evidence), INFERENCE (reasonable technical deduction), and UNKNOWN.
4. SECURITY & SECRETS:
   - Never reveal, unmask, or repeat secrets, passwords, or credentials.
   - Never claim to have executed, tested, or run the project's code. This is static analysis and AST inspection only.
5. CONCISENESS & CLARITY:
   - Write clear, structured developer-first responses using markdown (bullets, code references, sections).
   - Return valid JSON conforming to the requested schema:
     {
       "answer": "...",
       "sources": [
         {
           "file_path": "...",
           "line_start": 10,
           "line_end": 45,
           "reason": "..."
         }
       ]
     }
"""


def build_qa_prompt(
    context: Any,
    question: str,
    conversation_history: Optional[list] = None,
) -> str:
    """Builds a grounded prompt containing retrieved codebase context and conversation history."""
    sections = []

    sections.append(f"=== PROJECT OVERVIEW: {context.project_name} ===")
    sections.append(context.scan_overview)

    if context.deterministic_evidence:
        sections.append("\n=== DETERMINISTIC STATIC ANALYSIS FINDINGS ===")
        sections.extend(context.deterministic_evidence)

    if context.code_snippets:
        sections.append("\n=== RETRIEVED SOURCE CODE SNIPPETS (READ-ONLY & MASKED) ===")
        for s in context.code_snippets:
            sections.append(f"--- File: {s.file_path} (Lines {s.line_start} - {s.line_end}) ---")
            sections.append("```")
            sections.append(s.content)
            sections.append("```")

    if conversation_history:
        sections.append("\n=== RECENT CONVERSATION HISTORY ===")
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            sections.append(f"{role}: {content}")

    sections.append("\n=== DEVELOPER QUESTION ===")
    sections.append(question)
    sections.append(
        "\nProvide a technical, grounded response in valid JSON following the schema:\n"
        "- answer: string\n"
        "- sources: array of objects { file_path, line_start, line_end, reason }"
    )

    return "\n".join(sections)


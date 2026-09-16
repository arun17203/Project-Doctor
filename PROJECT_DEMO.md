# Project Doctor — Evaluator Walkthrough & Technical Interview Guide

This guide is structured for a **3 to 5-minute live demonstration** or technical viva voce examination (e.g., MCA Final Year Project Defense, Technical Interviews, Portfolio Review).

---

## 1. Executive Pitch (30 Seconds)

> *"Good morning. Today I am presenting **Project Doctor**, a multi-stage static code analysis and codebase intelligence platform designed as a 'Doctor for Software.'*
>
> *Modern teams struggle with technical debt, hidden vulnerabilities, and opaque dependency trees. Project Doctor provides a deterministic, zero-code-execution diagnostic engine that audits code quality, security vulnerabilities, dependencies, and architectural modularity, coupled with grounded generative AI explanations."*

---

## 2. Live Demonstration Script (3–4 Minutes)

### Step 1: Authentication & Project Ingestion (45s)
1. **Show Login / Register**:
   - Log in with `alice@doctor.io` or register a new user.
   - Point out: Secure JWT authentication with BCrypt hashing, multi-tenant workspace isolation.
2. **Create New Project**:
   - Name: `Demo Vulnerability Suite`.
   - Upload `demo.zip` (compressed from `demo_repository/`).
   - Mention: *"Notice that the upload pipeline enforces ZIP-Slip protection and path canonicalization. Untrusted code is sandboxed and never executed."*

### Step 2: Running Deterministic Diagnostics (60s)
1. **Repository Scanner (Stage 4)**:
   - Click **Run Scan**.
   - Show file discovery, language breakdown (Python, TypeScript), total code/comment lines, and directory tree.
2. **Code Quality & Security Audits (Stages 5 & 6)**:
   - Run Quality Analysis: Highlights Radon cyclomatic complexity ($M > 10$) in `evaluate_access_permissions` and Maintainability Index scores.
   - Run Security Audit: Displays identified critical vulnerabilities:
     - Hardcoded AWS Access Keys (`SEC001`)
     - SQL Injection via string formatting (`SEC002`)
     - Dynamic `eval()` execution (`SEC003`)
     - Insecure MD5 cryptographic hashing (`SEC004`)
   - Click **View Snippet** to demonstrate syntax-highlighted source context with inline line indicators.

### Step 3: Architecture Graph & Dependency Audit (45s)
1. **Interactive Architecture Visualizer (Stage 8)**:
   - Switch to the **Architecture Graph** tab.
   - Show interactive node diagram with color-coded architectural layers (*API, Service, Data, Presentation*).
   - Point out the red highlighted circular dependency: `auth_service.py` $\leftrightarrow$ `user_service.py`.
   - Explain: *"Our engine uses Tarjan's Strongly Connected Components algorithm to find cyclic dependencies in linear time."*
2. **Dependency Audit (Stage 7)**:
   - Review pinned dependencies (`flask==0.12.0`, `requests==2.18.4`) flagged for known CVE vulnerabilities via Google OSV integration.

### Step 4: Health Score, Technical Debt, & AI Explainer (60s)
1. **Health Engine (Stage 9)**:
   - Show overall weighted health score (e.g., $54/100$) and estimated technical debt ($18.5$ hours).
   - Review **Fix First Recommendations**: Priority-ranked action items addressing high-severity issues first.
2. **AI Problem Explainer (Stage 10)**:
   - Click **Explain with AI** on the SQL Injection finding.
   - Emphasize: *"Notice that deterministic analysis found the problem. The AI's job is strictly grounded explanation: it details the root cause, downstream impact, and provides copy-ready remediation code."*
3. **Ask My Codebase (Stage 11)**:
   - Ask: *"Where is user authentication implemented?"*
   - Show grounded response with verified citations (`backend/auth_service.py:L10-25`). Hallucinated citations are stripped by the engine.

### Step 5: History & Trends (30s)
1. Switch to **History & Trends (Stage 12)**.
2. Show snapshot timeline comparing Version 1 and Version 2.
3. Review metric deltas ($\Delta$ Health Score, $\Delta$ Debt Hours, resolved vs. newly introduced issues).

---

## 3. Technical Defense & Architecture Q&A

### Q1: Why not just use SonarQube or ESLint?
> *"Tools like ESLint are language-specific linter tools, whereas SonarQube is an enterprise scanner requiring extensive server infrastructure and compile-time hooks. Project Doctor provides a lightweight, unified, multi-language platform combining AST quality inspection, security rules, dependency vulnerability checking, and interactive architectural graphs with grounded LLM explanations in a single containerized solution."*

### Q2: How do you prevent untrusted user code from harming the server?
> *"Through our **Zero Code Execution Guarantee**. We never compile, import, or run user code. All analyses parse source files as raw text into Abstract Syntax Trees using Python's standard `ast` library or regex tokenizers. Furthermore, uploads enforce strict ZIP-Slip path canonicalization, and clones run in sandboxed directories with `.git` metadata stripped immediately."*

### Q3: How does the AI Explainer avoid hallucinations?
> *"The deterministic static analyzers detect the exact issue, rule ID, file, line number, and AST context first. This structured telemetry—with sensitive passwords and tokens automatically redacted—is supplied to Google Gemini with a constrained JSON schema. Gemini does not 'find' bugs; it explains pre-verified bugs."*

### Q4: How is technical debt calculated?
> *"Technical debt hours are deterministic, derived from weighted penalty hours assigned to specific issue categories: Critical Security issues add 4 hours, High Quality issues add 2 hours, Outdated Dependencies add 1.5 hours, and Architectural Cycles add 3 hours. This ensures reproducible and auditable estimations across analysis runs."*

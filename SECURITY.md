# Security Policy & Architecture Defense

## Overview

Project Doctor is designed with defense-in-depth principles to inspect untrusted source code repositories safely without exposing the host operating system, database, or surrounding infrastructure to malicious payloads.

---

## Core Security Guarantees

### 1. Zero Code Execution Guarantee
- **Untrusted Source Code**: Analyzed code is treated as passive text data.
- **AST Parsing**: Languages are analyzed via syntax-tree representations (e.g. Python's standard `ast.parse()`, regex lexical scanning) rather than running dynamic interpreters (`exec()`, `eval()`, or `importlib`).
- **Isolation**: Neither tests nor production endpoints invoke user-submitted executables, scripts, or package installation routines (`pip install`, `npm install`).

### 2. Archive & Ingestion Defense
- **ZIP Slip Protection**: Extraction validates target path canonicalization using `os.path.commonpath`. Any member file attempting relative directory traversal (e.g. `../../etc/passwd` or `..\Windows\System32`) raises an explicit `SecurityException` and immediately aborts the upload.
- **Symlink Disallowance**: Symbolic and hard links within archives are ignored or rejected during extraction to prevent host file disclosure.
- **Archive Size & Compression Bombs**: Zip archives exceeding `MAX_UPLOAD_SIZE_MB` (default 50MB) or uncompressed size thresholds are blocked.

### 3. Remote Git Repository Isolation
- **URL Whitelisting**: Clones are restricted exclusively to standard GitHub repository URLs (`https://github.com/...`). Non-GitHub domains, local file URIs (`file://`), and internal network addresses are rejected.
- **Shallow Cloning**: Repositories are cloned with `--depth 1` into isolated temporary scratch directories with timeout limits.
- **Metadata Stripping**: The cloned `.git` folder is completely wiped immediately following checkout, preventing git-hook execution or credential leakage.

### 4. Data Privacy & AI Prompt Sanitization
- **Sensitive File Exclusion**: `.env`, `.pem`, `.key`, `.p12`, `credentials.json`, and database dump files are prohibited from AI analysis context windows.
- **Secret Redaction**: Any source lines sent to Google Gemini for AI Problem Explanation or Codebase Q&A pass through regex redaction filters that replace detected API tokens, AWS keys, and passwords with `***REDACTED***`.

---

## Reporting a Security Vulnerability

If you discover a security vulnerability in Project Doctor, please report it responsibly:

1. Do NOT file a public issue on GitHub.
2. Email details to: `security@projectdoctor.dev` (or the repository maintainers).
3. Include:
   - A clear description of the vulnerability.
   - Steps or proof-of-concept repository archive to reproduce.
   - Potential impact.
4. The team will acknowledge receipt within 48 hours and work with you on a coordinated fix and advisory release.

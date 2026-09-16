import os
import re

LAYER_PRESENTATION = "Presentation"
LAYER_API = "API"
LAYER_SERVICE = "Service"
LAYER_DATA = "Data"
LAYER_UTILITY = "Utility"
LAYER_CONFIGURATION = "Configuration"
LAYER_TEST = "Test"
LAYER_UNKNOWN = "Unknown"

# Directory / filename patterns for each layer (checked in priority order)
TEST_PATTERNS = [
    r"(?:^|[/\\])(?:tests?|__tests__|specs?)(?:[/\\]|$)",
    r"(?:^|[/\\])(?:test_|.*_test\.|.*\.test\.|.*\.spec\.)",
]

API_PATTERNS = [
    r"(?:^|[/\\])(?:routes?|controllers?|api|endpoints?|handlers?|routers?)(?:[/\\]|$)",
    r".*(?:controller|route|router|endpoint|api)\.(?:py|js|ts|jsx|tsx)$",
]

SERVICE_PATTERNS = [
    r"(?:^|[/\\])(?:services?|business|usecases?|managers?|workflows?|tasks?|jobs?|workers?)(?:[/\\]|$)",
    r".*(?:service|manager|workflow|worker|task)\.(?:py|js|ts|jsx|tsx)$",
]

DATA_PATTERNS = [
    r"(?:^|[/\\])(?:models?|repositories?|database|db|schemas?|entities?|dao|migrations?|alembic)(?:[/\\]|$)",
    r".*(?:model|repository|schema|entity|dao|migration)\.(?:py|js|ts|jsx|tsx)$",
]

PRESENTATION_PATTERNS = [
    r"(?:^|[/\\])(?:components?|pages?|views?|screens?|ui|templates?|layouts?)(?:[/\\]|$)",
    r".*\.(?:jsx|tsx|vue|svelte)$",
]

CONFIG_PATTERNS = [
    r"(?:^|[/\\])(?:configs?|settings?|constants?|environments?)(?:[/\\]|$)",
    r".*(?:config|settings|environment|constant|constants)\.(?:py|js|ts|json)$",
]

UTILITY_PATTERNS = [
    r"(?:^|[/\\])(?:utils?|helpers?|common|lib|shared|tools?)(?:[/\\]|$)",
    r".*(?:util|utils|helper|helpers|common)\.(?:py|js|ts|jsx|tsx)$",
]


def classify_layer(file_path: str) -> str:
    """Classify a source file into an architectural layer based on deterministic heuristic rules.
    This classification is strictly heuristic/inferred.
    """
    normalized = file_path.replace("\\", "/").lower()

    # 1. Test Layer (checked first to avoid mistaking test controllers or test models)
    for pat in TEST_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_TEST

    # 2. Presentation Layer
    for pat in PRESENTATION_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_PRESENTATION

    # 3. API Layer
    for pat in API_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_API

    # 4. Service Layer
    for pat in SERVICE_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_SERVICE

    # 5. Data Layer
    for pat in DATA_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_DATA

    # 6. Configuration Layer
    for pat in CONFIG_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_CONFIGURATION

    # 7. Utility Layer
    for pat in UTILITY_PATTERNS:
        if re.search(pat, normalized):
            return LAYER_UTILITY

    return LAYER_UNKNOWN

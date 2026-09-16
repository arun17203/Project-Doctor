import json
import logging
import os
from typing import Optional
from backend.app.core.config import settings
from backend.app.ai.prompts import SYSTEM_INSTRUCTION, QA_SYSTEM_INSTRUCTION
from backend.app.ai.schemas import AIExplanationOutput, CodebaseQAOutput

logger = logging.getLogger(__name__)


class AIUnavailableError(Exception):
    """Raised when Gemini API is unconfigured or unavailable."""
    pass


class AIExplanationError(Exception):
    """Raised when Gemini API call fails during generation."""
    pass


class GeminiClient:
    """Wrapper around official google-genai SDK for Project Doctor."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model = model or settings.GEMINI_MODEL or "gemini-2.5-flash"
        self._client = None

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

    def is_available(self) -> bool:
        """Returns True if a non-empty API key is present."""
        key = self.api_key
        return bool(key and key.strip() and key != "your_gemini_api_key_here")

    def _get_client(self):
        if not self.is_available():
            raise AIUnavailableError(
                "AI explanation is currently unavailable. GEMINI_API_KEY is not configured in the backend environment. The underlying analysis is still available."
            )
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google-genai client: {e}")
                raise AIUnavailableError(
                    "AI explanation client could not be initialized. The underlying analysis is still available."
                )
        return self._client

    def generate_explanation(self, prompt: str) -> AIExplanationOutput:
        """Calls Google Gemini with structured output schema."""
        client = self._get_client()

        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_json_schema=AIExplanationOutput.model_json_schema(),
                    temperature=0.2,
                ),
            )

            if not response or not response.text:
                raise AIExplanationError(
                    "AI explanation could not be generated: Empty response received from provider."
                )

            data = json.loads(response.text)
            return AIExplanationOutput(**data)

        except (AIUnavailableError, AIExplanationError):
            raise
        except json.JSONDecodeError as jde:
            logger.warning(f"Failed to parse structured JSON from Gemini response: {jde}")
            raise AIExplanationError(
                "AI explanation could not be formatted properly. Your analysis results are still available."
            )
        except Exception as e:
            # Mask any inadvertent key exposure in log message
            err_msg = str(e)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "***KEY***")
            logger.error(f"Gemini generation error: {err_msg}")
            raise AIExplanationError(
                "AI explanation could not be generated right now. Your analysis results are still available."
            )

    def generate_qa_answer(self, prompt: str) -> CodebaseQAOutput:
        """Calls Google Gemini with CodebaseQAOutput structured schema."""
        client = self._get_client()

        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=QA_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_json_schema=CodebaseQAOutput.model_json_schema(),
                    temperature=0.2,
                ),
            )

            if not response or not response.text:
                raise AIExplanationError(
                    "AI response could not be generated: Empty response received from provider."
                )

            data = json.loads(response.text)
            return CodebaseQAOutput(**data)

        except (AIUnavailableError, AIExplanationError):
            raise
        except json.JSONDecodeError as jde:
            logger.warning(f"Failed to parse structured JSON from Gemini QA response: {jde}")
            raise AIExplanationError(
                "AI answer could not be formatted properly. Please try rephrasing your question."
            )
        except Exception as e:
            err_msg = str(e)
            if self.api_key and self.api_key in err_msg:
                err_msg = err_msg.replace(self.api_key, "***KEY***")
            logger.error(f"Gemini QA error: {err_msg}")
            raise AIExplanationError(
                "AI answer could not be generated right now. Your project data is still available."
            )


# Default singleton instance
gemini_client = GeminiClient()

"""
Groq LLM Adapter — config-driven model selection with retry resilience.

To swap models, change LLM_MODEL_NAME in your .env:
    LLM_MODEL_NAME=llama-3.3-70b-versatile
"""
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.interfaces.llm import ILLM
from app.core.logger import logger


class GroqAdapter(ILLM):
    def __init__(self, api_key: str, model_name: str, timeout: int = 30, max_retries: int = 3):
        if not api_key:
            raise ValueError("Missing Groq API key — set GROQ_API_KEY in .env")
        self.client = Groq(api_key=api_key, timeout=timeout)
        self.model_name = model_name
        self.max_retries = max_retries
        logger.info(f"Groq adapter initialized | model={model_name} | timeout={timeout}s")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"Groq call failed (attempt {retry_state.attempt_number}), retrying..."
        ),
    )
    def generate_response(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"Groq chat call failed (attempt {retry_state.attempt_number}), retrying..."
        ),
    )
    def chat_with_messages(self, messages: list, temperature: float = 0.0) -> str:
        """Full message list call — used by ChatService for history-aware conversations."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            temperature=temperature,
            messages=messages,
        )
        return response.choices[0].message.content
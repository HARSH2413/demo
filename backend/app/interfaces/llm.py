from abc import ABC, abstractmethod


class ILLM(ABC):
    @abstractmethod
    def generate_response(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        """
        Sends the strict prompt to the AI and returns the secure answer.
        Temperature defaults to 0.0 to enforce the anti-hallucination policy.
        """
        pass

    @abstractmethod
    def chat_with_messages(self, messages: list, temperature: float = 0.0) -> str:
        """
        Full message list call for history-aware conversations.
        Used by ChatService to pass system prompt + chat history together.
        """
        pass
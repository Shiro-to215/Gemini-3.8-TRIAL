from .conversation import ConversationManager
from .fallback import FallbackManager
from .gemini_client import GeminiClient
from .memory import MemoryManager


class ChatController:
    def __init__(self, conversations: ConversationManager, memories: MemoryManager, client: GeminiClient, fallback: FallbackManager):
        self.conversations = conversations
        self.memories = memories
        self.client = client
        self.fallback = fallback

    def send(self, conversation_id: str, message: str) -> dict:
        if not message.strip():
            raise ValueError("Message cannot be empty")
        if not self.conversations.get(conversation_id):
            raise KeyError(conversation_id)
        history = self.conversations.prompt_history(conversation_id)
        memory = self.memories.prompt_context()
        self.conversations.add_message(conversation_id, "user", message.strip())
        response, model, switched = self.fallback.generate(
            lambda selected_model: self.client.generate(selected_model, history, memory, message.strip())
        )
        self.conversations.add_message(conversation_id, "model", response, model)
        self.conversations.rename_from_first_message(conversation_id, message)
        return {"response": response, "model": model, "switched": switched, "conversation": self.conversations.get(conversation_id)}
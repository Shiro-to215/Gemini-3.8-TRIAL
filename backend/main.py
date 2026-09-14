from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .chat import ChatController
from .config import settings
from .conversation import ConversationManager
from .database import Database
from .fallback import AllModelsUnavailable, FallbackManager
from .gemini_client import GeminiClient, GeminiRequestError
from .memory import MemoryManager
from .model_manager import ModelManager


database = Database(settings.database_path)
conversations = ConversationManager(database)
memories = MemoryManager(database)
model_manager = ModelManager(database)
controller = ChatController(conversations, memories, GeminiClient(), FallbackManager(model_manager))

app = FastAPI(title="Personal Gemini Chat")
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=20000)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/api/conversations")
def list_conversations() -> list[dict]:
    return conversations.list()


@app.post("/api/conversations")
def create_conversation() -> dict:
    return conversations.create()


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    conversation = conversations.get(conversation_id)
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str) -> dict:
    if not conversations.delete(conversation_id):
        raise HTTPException(404, "Conversation not found")
    return {"ok": True}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    try:
        return controller.send(request.conversation_id, request.message)
    except KeyError as error:
        raise HTTPException(404, "Conversation not found") from error
    except AllModelsUnavailable as error:
        raise HTTPException(503, "現在利用可能なモデルがありません。しばらくしてから再試行してください。") from error
    except GeminiRequestError as error:
        raise HTTPException(502, error.message) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/api/memory")
def list_memory() -> list[dict]:
    return memories.list()


@app.post("/api/memory")
def create_memory(request: MemoryRequest) -> dict:
    try:
        return memories.create(request.content)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.put("/api/memory/{memory_id}")
def update_memory(memory_id: int, request: MemoryRequest) -> dict:
    try:
        result = memories.update(memory_id, request.content)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    if not result:
        raise HTTPException(404, "Memory not found")
    return result


@app.delete("/api/memory/{memory_id}")
def delete_memory(memory_id: int) -> dict:
    if not memories.delete(memory_id):
        raise HTTPException(404, "Memory not found")
    return {"ok": True}


@app.get("/api/status")
def status() -> dict:
    return {"current_model": model_manager.current() if model_manager.available_models() else None, "models": model_manager.statuses(), "configured": bool(settings.gemini_api_key)}
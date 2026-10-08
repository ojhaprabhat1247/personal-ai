import json
import logging
from dataclasses import asdict

import anyio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from chat_service import ChatService
from chat_router import PrivacyMode

logger = logging.getLogger(__name__)
app = FastAPI(title="Personal AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = ChatService()


class ChatRequest(BaseModel):
    message: str
    privacy_mode: str = "auto"


class ChatResponse(BaseModel):
    reply: str
    privacy_mode: str
    sensitive: bool
    sensitivity_reasons: list[str]


def validate_request(request):
    try:
        privacy_mode = PrivacyMode(request.privacy_mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid privacy_mode. Use: local_only, privacy_first, auto, max_quality",
        ) from None
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return privacy_mode


@app.get("/health")
def health():
    return {"status": "ok", "service": "personal-ai"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    privacy_mode = validate_request(request)
    try:
        result = chat_service.chat(request.message, privacy_mode)
        return ChatResponse(**asdict(result))
    except Exception as error:
        logger.error("Chat request failed (%s).", type(error).__name__)
        raise HTTPException(
            status_code=500,
            detail="Unable to complete the chat request. Check the backend and local model service.",
        ) from None


class ChatStreamingResponse(StreamingResponse):
    """Close the generator even if sending to a disconnected browser raises."""

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()


@app.post("/chat/reset")
def reset_chat():
    try:
        chat_service.reset_chat()
        return {"status": "ok"}
    except Exception as error:
        logger.error("Chat reset failed (%s).", type(error).__name__)
        raise HTTPException(
            status_code=500,
            detail="Unable to start a new chat. Your conversation has been kept.",
        ) from None


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    privacy_mode = validate_request(request)

    async def events():
        stream = chat_service.stream_chat(request.message, privacy_mode)
        try:
            while True:
                # Keep synchronous retrieval/model/persistence work off the event loop.
                event = await run_in_threadpool(next, stream, None)
                if event is None:
                    break
                data = json.dumps(event.data, ensure_ascii=False)
                yield f"event: {event.event}\ndata: {data}\n\n"
        except Exception as error:
            logger.error("Chat stream failed (%s).", type(error).__name__)
            data = json.dumps({
                "code": "generation_failed",
                "message": "The response could not be completed. Check the backend and local model service.",
            })
            yield f"event: error\ndata: {data}\n\n"
        finally:
            # A blocking provider read may finish before disconnect cleanup runs.
            with anyio.CancelScope(shield=True):
                await run_in_threadpool(stream.close)

    return ChatStreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

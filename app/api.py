from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from chat_service import ChatService
from chat_router import PrivacyMode
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Personal AI API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "personal-ai"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    try:
        privacy_mode = PrivacyMode(
            request.privacy_mode
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid privacy_mode. "
                "Use: local_only, privacy_first, auto, max_quality"
            )
        )

    try:
        result = chat_service.chat(
            user_input=request.message,
            privacy_mode=privacy_mode
        )

        return ChatResponse(
            reply=result.reply,
            privacy_mode=result.privacy_mode,
            sensitive=result.sensitive,
            sensitivity_reasons=result.sensitivity_reasons
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
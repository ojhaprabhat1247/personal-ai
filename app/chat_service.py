import json
import logging
from dataclasses import dataclass
from threading import Lock

import memory
import profile
import retriever
import memory_classifier
import memory_manager

from privacy_guard import PrivacyGuard, PrivacyResult
from chat_router import ChatRouter, ChatRoutingRequest, PrivacyMode, close_stream

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    reply: str
    privacy_mode: str
    sensitive: bool
    sensitivity_reasons: list[str]


@dataclass
class ChatEvent:
    event: str
    data: dict


class ChatService:
    # This prototype shares one persisted history/profile. Serialize entire turns
    # so overlapping requests cannot mix context or interleave history writes.
    _turn_lock = Lock()

    def __init__(self):
        profile.load_profile()
        memory.load_memory()
        self.chat_router = ChatRouter()
        self.privacy_guard = PrivacyGuard()

    def reset_chat(self):
        # Wait for any active turn before resetting so it cannot later repopulate
        # the newly cleared history. Profile and semantic memory are independent.
        with self._turn_lock:
            memory.reset_chat()

    def _prepare(self, user_input, privacy_mode, *, stream):
        user_input = user_input.strip()
        if not user_input:
            raise ValueError("Message cannot be empty.")

        profile_text = (
            json.dumps(profile.profile, ensure_ascii=False)
            if profile.profile else "No profile available."
        )
        context = retriever.retrieve_context(user_input, profile_text)

        # Check actual background data and dialogue, excluding our own instructions.
        reasons = []
        for message in context[1:]:
            for reason in self.privacy_guard.analyze(message["content"]).reasons:
                if reason not in reasons:
                    reasons.append(reason)
        privacy = PrivacyResult(sensitive=bool(reasons), reasons=reasons)
        request = ChatRoutingRequest(
            messages=context,
            privacy_mode=privacy_mode,
            sensitive=privacy.sensitive,
            stream=stream,
        )
        return user_input, request, privacy

    def _finalize(self, user_input, reply, privacy_mode, privacy):
        if not reply.strip():
            raise RuntimeError("The model returned an empty response.")

        result = ChatResult(
            reply=reply,
            privacy_mode=privacy_mode.value,
            sensitive=privacy.sensitive,
            sensitivity_reasons=privacy.reasons,
        )

        # Commit a complete pair only. Failed/closed streams never reach this point.
        start = len(memory.messages)
        memory.add_message("user", user_input)
        memory.add_message("assistant", reply)
        try:
            memory.save_memory()
        except Exception:
            del memory.messages[start:]
            raise

        # Auxiliary model calls happen after answer generation. A failed extraction
        # must not turn an already-completed answer into an apparent request failure.
        try:
            if not user_input.lower().startswith(
                ("what", "who", "where", "when", "why", "how")
            ):
                decision = memory_classifier.classify(user_input)
                if decision.get("save"):
                    memory_manager.save_memory(
                        text=user_input,
                        category=decision.get("category", "general"),
                        importance=decision.get("importance", 1),
                    )
        except Exception:
            logger.warning("Could not update semantic memory for the completed turn.")

        try:
            keywords = (
                "my name", "i am", "i'm", "city", "live",
                "profession", "age", "python", "favorite",
            )
            if any(word in user_input.lower() for word in keywords):
                profile.update_profile(user_input)
        except Exception:
            logger.warning("Could not update the profile for the completed turn.")

        return result

    def chat(self, user_input, privacy_mode=PrivacyMode.AUTO) -> ChatResult:
        with self._turn_lock:
            user_input, request, privacy = self._prepare(
                user_input, privacy_mode, stream=False
            )
            response = self.chat_router.generate(request)
            return self._finalize(
                user_input, response["message"]["content"], privacy_mode, privacy
            )

    def stream_chat(self, user_input, privacy_mode=PrivacyMode.AUTO):
        with self._turn_lock:
            user_input, request, privacy = self._prepare(
                user_input, privacy_mode, stream=True
            )
            stream = self.chat_router.generate(request)
            parts = []
            try:
                for chunk in stream:
                    text = chunk["message"]["content"]
                    if text:
                        parts.append(text)
                        yield ChatEvent("delta", {"text": text})
            finally:
                close_stream(stream)
            result = self._finalize(
                user_input, "".join(parts), privacy_mode, privacy
            )

        # Release the shared-history lock before delivering the terminal event.
        yield ChatEvent("done", {
            "privacy_mode": result.privacy_mode,
            "sensitive": result.sensitive,
            "sensitivity_reasons": result.sensitivity_reasons,
        })

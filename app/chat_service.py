import json
from dataclasses import dataclass

import memory
import profile
import retriever
import memory_classifier
import memory_manager

from privacy_guard import PrivacyGuard
from chat_router import (
    ChatRouter,
    ChatRoutingRequest,
    PrivacyMode,
)


@dataclass
class ChatResult:
    reply: str
    privacy_mode: str
    sensitive: bool
    sensitivity_reasons: list[str]


class ChatService:

    def __init__(self):
        profile.load_profile()
        memory.load_memory()

        self.chat_router = ChatRouter()
        self.privacy_guard = PrivacyGuard()

    def chat(
        self,
        user_input: str,
        privacy_mode: PrivacyMode = PrivacyMode.AUTO,
    ) -> ChatResult:

        user_input = user_input.strip()

        if not user_input:
            raise ValueError("Message cannot be empty.")

        # Store current message first because the existing
        # retriever reads recent chat from memory.messages.
        memory.add_message(
            "user",
            user_input
        )

        # Decide whether this message is useful
        # enough for long-term semantic memory.
        if not user_input.lower().startswith(
            (
                "what",
                "who",
                "where",
                "when",
                "why",
                "how",
            )
        ):
            decision = memory_classifier.classify(
                user_input
            )

            if decision.get("save"):
                memory_manager.save_memory(
                    text=user_input,
                    category=decision.get(
                        "category",
                        "general"
                    ),
                    importance=decision.get(
                        "importance",
                        1
                    )
                )

        if profile.profile:
            profile_text = json.dumps(
                profile.profile,
                indent=4
            )
        else:
            profile_text = "No profile available."

        privacy_result = self.privacy_guard.analyze(
            user_input
        )

        context_messages = retriever.retrieve_context(
            user_input,
            profile_text
        )

        response = self.chat_router.generate(
            ChatRoutingRequest(
                messages=context_messages,
                privacy_mode=privacy_mode,
                sensitive=privacy_result.sensitive,
                stream=False
            )
        )

        ai_reply = response["message"]["content"]

        memory.add_message(
            "assistant",
            ai_reply
        )

        keywords = [
            "my name",
            "i am",
            "i'm",
            "city",
            "live",
            "profession",
            "age",
            "python",
            "favorite",
        ]

        if any(
            word in user_input.lower()
            for word in keywords
        ):
            profile.update_profile(
                user_input
            )

        memory.save_memory()

        return ChatResult(
            reply=ai_reply,
            privacy_mode=privacy_mode.value,
            sensitive=privacy_result.sensitive,
            sensitivity_reasons=privacy_result.reasons,
        )
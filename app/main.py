import json

import memory
import profile
import vectordb
import retriever
import memory_classifier
import memory_manager
from privacy_guard import PrivacyGuard

from chat_router import (
    ChatRouter,
    ChatRoutingRequest,
    PrivacyMode,
)


vectordb.show_all()

print("=" * 50)
print("🤖 Personal AI with Memory")
print("Type 'exit' to quit")
print("=" * 50)

profile.load_profile()
memory.load_memory()

chat_router = ChatRouter()
privacy_guard = PrivacyGuard()
current_privacy_mode = PrivacyMode.AUTO


while True:

    user_input = input("\n🧑 You: ")

    if user_input.lower() == "exit":
        print("\n👋 Goodbye!")
        break


    if user_input.lower() == "/local":
        current_privacy_mode = PrivacyMode.LOCAL_ONLY
        print("🔒 Mode: LOCAL ONLY")
        continue

    if user_input.lower() == "/privacy":
        current_privacy_mode = PrivacyMode.PRIVACY_FIRST
        print("🛡️ Mode: PRIVACY FIRST")
        continue

    if user_input.lower() == "/auto":
        current_privacy_mode = PrivacyMode.AUTO
        print("⚡ Mode: AUTO")
        continue

    if user_input.lower() == "/quality":
        current_privacy_mode = PrivacyMode.MAX_QUALITY
        print("🚀 Mode: MAX QUALITY")
        continue

    if user_input.lower() == "/mode":
        print(
            "Current mode:",
            current_privacy_mode.value
        )
        continue

    memory.add_message(
        "user",
        user_input
    )

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

        print(decision)

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

    try:

        if profile.profile:
            profile_text = json.dumps(
                profile.profile,
                indent=4
            )
        else:
            profile_text = (
                "No profile available."
            )

        privacy_result = privacy_guard.analyze(
            user_input
        )
        
        context_messages = (
            retriever.retrieve_context(
                user_input,
                profile_text
            )
        )

        response = chat_router.generate(
            ChatRoutingRequest(
                messages=context_messages,
                privacy_mode=current_privacy_mode,
                sensitive=privacy_result.sensitive,
                stream=True
            )
        )

        print("\n🤖 AI:\n")

        ai_reply = ""

        for chunk in response:

            content = (
                chunk["message"]["content"]
            )

            print(
                content,
                end="",
                flush=True
            )

            ai_reply += content

        print()

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

    except Exception as e:
        print(
            f"\n❌ Error: {e}"
        )
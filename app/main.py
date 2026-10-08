from chat_service import ChatService
from chat_router import PrivacyMode


def main():
    print("=" * 50)
    print("🤖 Personal AI with Memory")
    print("Type 'exit' to quit")
    print("=" * 50)

    service = ChatService()
    current_privacy_mode = PrivacyMode.AUTO
    modes = {
        "/local": PrivacyMode.LOCAL_ONLY,
        "/privacy": PrivacyMode.PRIVACY_FIRST,
        "/auto": PrivacyMode.AUTO,
        "/quality": PrivacyMode.MAX_QUALITY,
    }

    while True:
        user_input = input("\n🧑 You: ")
        command = user_input.strip().lower()
        if command == "exit":
            print("\n👋 Goodbye!")
            break
        if command in modes:
            current_privacy_mode = modes[command]
            print("Mode:", current_privacy_mode.value)
            continue
        if command == "/mode":
            print("Current mode:", current_privacy_mode.value)
            continue

        stream = service.stream_chat(user_input, current_privacy_mode)
        try:
            print("\n🤖 AI:\n")
            for event in stream:
                if event.event == "delta":
                    print(event.data["text"], end="", flush=True)
            print()
        except Exception as error:
            print(f"\n❌ Error: {error}")
        finally:
            stream.close()


if __name__ == "__main__":
    main()

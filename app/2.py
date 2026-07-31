import json
from ollama import chat

messages = [
    {
        "role": "system",
        "content": """
You are a helpful AI assistant.

Rules:
- Default answer should be short (2-5 lines).
- Answer directly.
Language Rules:

- If the user writes in English, ALWAYS reply in English.
- If the user writes in Hindi, reply in Hindi.
- If the user writes in Hinglish, reply in Hinglish.
- Never change the user's language unless explicitly asked.
- If the user asks for details, then explain in detail.
- If the user asks for code, write clean code.
- Never add unnecessary examples.
- Never repeat information.
"""
    }
]

profile={}

print("=" * 50)
print("🤖 Personal AI with Memory")
print("Type 'exit' to quit")
print("=" * 50)
def add_message(role, content):
    messages.append(
        {
            "role": role,
            "content": content
        }
    )

def load_profile():
    global profile

    try:
        with open("profile.json", "r") as file:
            profile = json.load(file)

    except FileNotFoundError:
        print("⚠️ No profile found.")

def load_memory():
    global messages

    try:
        with open("memory.json", "r") as file:
            old_messages = json.load(file)

        messages.extend(old_messages)

    except FileNotFoundError:
        print("⚠️ No previous memory found.")
def save_memory():
    with open("memory.json", "w") as file:
        json.dump(messages[1:], file, indent=4,ensure_ascii=False)


def save_profile():
    with open("profile.json", "w") as file:
        json.dump(profile, file, indent=4,ensure_ascii=False)

def update_profile(user_input):
    response = chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": """
You extract user information.

Return ONLY a valid JSON object.

Do not explain anything.
Do not use markdown.
Do not write ```json.
Do not add any text before or after JSON.

Only extract information explicitly provided by the user.

Never guess.

If a field is missing, do not include it.

Possible fields:

- name
- city
- profession
- age
- favorite_language

If nothing is found return {}.


"""
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )
    reply = response["message"]["content"]

    try:
        data = json.loads(reply)

    except json.JSONDecodeError:
        print("⚠️ Invalid JSON received.")
        return

    allowed_fields = [
        "name",
        "city",
        "profession",
        "age",
        "favorite_language"
        ]

    for key in allowed_fields:
        if key in data:
            profile[key] = data[key]

    save_profile()

   

load_profile()
load_memory()    

def get_context():
    if profile:
        profile_text = json.dumps(profile, indent=4)
    else:
        profile_text = "No profile available."

    profile_message = {
        "role": "system",
        "content": f"""
        User Profile:

    {profile_text}
    """
    }

    return [
        messages[0],
        profile_message
    ] + messages[1:][-10:]
while True:

    user_input = input("\n🧑 You: ")

    if user_input.lower() == "exit":
        print("\n👋 Goodbye!")
        break

    add_message("user",user_input)
    
    try:
        response = chat(
        model="llama3.2",
        messages=get_context(),
        stream=True
        )

        print("\n🤖 AI:\n")

        ai_reply = ""

        for chunk in response:

            content = chunk["message"]["content"]

            print(content, end="", flush=True)

            ai_reply += content

        print()

        
        add_message("assistant", ai_reply)

        keywords = [
        "my name",
        "i am",
        "i'm",
        "city",
        "live",
        "profession",
        "age",
        "python",
        "favorite"
        ]

        if any(word in user_input.lower() for word in keywords):
            update_profile(user_input)

        save_memory()
        

    except Exception as e:
        print(f"\n❌ Error: {e}")

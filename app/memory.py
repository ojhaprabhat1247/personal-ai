import json
import string
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

def add_message(role, content):
    messages.append(
        {
            "role": role,
            "content": content
        }
    )


def load_memory():
    global messages

    try:
        with open("data/memory.json", "r",encoding="utf-8") as file:
            old_messages = json.load(file)

        messages.extend(old_messages)

    except FileNotFoundError:
        print("⚠️ No previous memory found.")
def save_memory():
    with open("data/memory.json", "w",encoding="utf-8") as file:
        json.dump(messages[1:], file, indent=4,ensure_ascii=False)
        


def get_context(profile_text, relevant_memory):

    profile_message = {
        "role": "system",
        "content": f"""
User Profile:

{profile_text}
"""
    }

    memory_text = ""

    for content in relevant_memory:

        memory_text += f"- {content}\n"

        # Questions ko skip karo
        if content.lower().startswith(
            ("what", "who", "where", "when", "why", "how")
        ):
            continue

        memory_text += f"- {content}\n"

    memory_message = {
        "role": "system",
        "content": f"""
Relevant User Memories:

{memory_text}

Instructions:
- These are retrieved from previous conversations.
- Use them only if they are relevant to the current question.
- If multiple memories conflict, prefer the most recent one.
- Do not invent new information.
"""
    }

    return [
        messages[0],
        profile_message,
        memory_message
    ] + messages[1:][-10:]



def extract_keywords(query):

    stop_words = [
        "what",
        "was",
        "is",
        "the",
        "a",
        "an",
        "my",
        "your",
        "do",
        "does",
        "did"
    ]

    words = query.lower().split()

    keywords = []

    for word in words:

        word = word.strip(string.punctuation)

        if word in stop_words:
            continue

        keywords.append(word)

    return keywords
def search_memory(query):

    keywords = extract_keywords(query)

    results = []

    for message in messages:

        if message["role"] != "user":
            continue

        content = message["content"].lower()

        score = 0

        for keyword in keywords:

            if keyword in content:
                score += 1

        if score > 0:
            results.append((score, message))

    results.sort(key=lambda x: x[0], reverse=True)

    top_messages = []

    for score, message in results:
        top_messages.append(message)

    return top_messages[:5]


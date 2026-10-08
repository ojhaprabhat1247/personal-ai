import json
import os
from pathlib import Path
import string
from tempfile import NamedTemporaryFile
from chat_prompts import CHAT_SYSTEM_PROMPT

MEMORY_PATH = Path("data/memory.json")

messages = [
    {
        "role": "system",
        "content": CHAT_SYSTEM_PROMPT
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
        with MEMORY_PATH.open("r", encoding="utf-8") as file:
            old_messages = json.load(file)

        messages.extend(old_messages)

    except FileNotFoundError:
        print("⚠️ No previous memory found.")
def _write_history(history):
    """Replace the history file atomically; failed writes keep the old history."""
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=MEMORY_PATH.parent,
            prefix="memory-", suffix=".tmp", delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(history, file, indent=4, ensure_ascii=False)
        os.replace(temporary_path, MEMORY_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def save_memory():
    _write_history(messages[1:])


def reset_chat():
    """Reset only conversational history, preserving the shared base instructions."""
    _write_history([])
    # Only change in-process context after persistence succeeds.
    messages[:] = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]



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


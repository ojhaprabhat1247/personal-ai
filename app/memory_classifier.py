import json
from ollama import chat

MODEL = "llama3.2"


def classify(text):

    response = chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
You are a memory classifier.

Your task is to decide if the user's message should be stored as long-term memory.

Rules:

Save only if it contains:

- Name
- Age
- City
- Profession
- Project
- Goal
- Preference
- Skill
- Education
- Personal fact

Do NOT save:

- Greetings
- Questions
- Small talk
- Jokes
- Temporary requests

Return ONLY valid JSON.

Format:

{
    "save": true,
    "category": "project",
    "importance": 5
}

or

{
    "save": false
}
"""
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    reply = response["message"]["content"]

    try:
        return json.loads(reply)

    except Exception:
        return {"save": False}
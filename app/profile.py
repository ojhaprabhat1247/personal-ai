import json
import llm

profile = {}


def load_profile():
    global profile

    try:
        with open("data/profile.json", "r", encoding="utf-8") as file:
            profile = json.load(file)

    except FileNotFoundError:
        print("⚠️ No profile found.")


def save_profile():
    with open("data/profile.json", "w", encoding="utf-8") as file:
        json.dump(profile, file, indent=4, ensure_ascii=False)


def update_profile(user_input):

    response = llm.generate(
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
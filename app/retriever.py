import memory
import vectordb

from chat_prompts import build_chat_messages


def get_recent_chat(limit=10):
    """Return bounded prior dialogue, excluding the system prompt."""
    return memory.messages[1:][-limit:]


def get_vector_memory(query):
    return vectordb.search_memory(query)


def retrieve_context(user_input, profile_text):
    # The current turn is not stored until generation completes successfully.
    return build_chat_messages(
        user_input,
        profile_text,
        get_recent_chat(),
        get_vector_memory(user_input),
    )

import memory
import vectordb


def get_recent_chat(limit=10):
    """
    Return the last N chat messages.
    Ignore the system prompt.
    """
    return memory.messages[1:][-limit:]


def get_vector_memory(query):
    """
    Search relevant long-term memories
    from ChromaDB.
    """
    return vectordb.search_memory(query)


def merge_context(recent_chat, vector_memory):
    """
    Merge recent chat and retrieved memories.
    Remove duplicate memories.
    """

    merged = []
    seen = set()

    # Recent Chat
    for message in recent_chat:

        merged.append(message)

        if message["role"] == "user":
            seen.add(message["content"].lower())

    # Long-Term Memory
    for memory_item in vector_memory:

        text = memory_item["text"]
        score = memory_item["score"]
        metadata = memory_item["metadata"]

        print(memory_item)

        if text.lower() in seen:
            continue

        merged.append(
            {
                "role": "system",
                "content": f"Relevant Memory: {text}"
            }
        )

        seen.add(text.lower())

    return merged


def retrieve_context(user_input, profile_text):

    profile_message = {
        "role": "system",
        "content": f"""
User Profile

{profile_text}
"""
    }

    recent_chat = get_recent_chat()

    vector_memory = get_vector_memory(user_input)

    final_context = merge_context(
        recent_chat,
        vector_memory
    )

    return [
        memory.messages[0],
        profile_message
    ] + final_context
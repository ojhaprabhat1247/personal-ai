import vectordb


def save_memory(text, category, importance):

    existing = vectordb.search_memory(text, n_results=1)

    if existing:

        best = existing[0]

        score = best["score"]

        # Agar similar memory already hai
        if score < 100:

            print("🟡 Similar memory already exists.")
            return

    vectordb.add_memory(
        text=text,
        category=category,
        importance=importance
    )

    print("✅ New memory stored.")
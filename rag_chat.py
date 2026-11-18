"""TF-IDF property retrieval and Ollama-based recommendation generation."""

from pathlib import Path

import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = Path(__file__).resolve().parent / "austinHousingData.csv"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:1b"

# Load and index the historical Austin property descriptions.
df = pd.read_csv(DATA_PATH)
df = df.dropna(subset=["description"]).copy()
df["description"] = df["description"].astype(str).str.strip()
df = df[df["description"] != ""].reset_index(drop=True)
df = df[df["description"].str.len() >= 100].reset_index(drop=True)

vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
house_vectors = vectorizer.fit_transform(df["description"])


def retrieve_houses(question, top_k=3, max_price=None, min_bedrooms=None):
    """Return the highest-scoring properties that satisfy numeric filters."""
    query_vector = vectorizer.transform([question])
    scores = cosine_similarity(query_vector, house_vectors).flatten()
    ranked_indices = scores.argsort()[::-1]

    matches = []
    for index in ranked_indices:
        house = df.iloc[index]
        price = pd.to_numeric(house.get("latestPrice"), errors="coerce")
        bedrooms = pd.to_numeric(house.get("numOfBedrooms"), errors="coerce")

        if max_price is not None and (pd.isna(price) or price > max_price):
            continue
        if min_bedrooms is not None and (
            pd.isna(bedrooms) or bedrooms < min_bedrooms
        ):
            continue

        matches.append((house, float(scores[index])))
        if len(matches) >= top_k:
            break

    return matches


def generate_answer(question, matches=None, max_price=None, min_bedrooms=None):
    """Generate a grounded recommendation using only the supplied matches."""
    if matches is None:
        matches = retrieve_houses(
            question,
            top_k=3,
            max_price=max_price,
            min_bedrooms=min_bedrooms,
        )

    if not matches:
        return "I couldn't find properties matching those preferences."

    context_blocks = []
    for number, (house, score) in enumerate(matches, start=1):
        price = pd.to_numeric(house.get("latestPrice"), errors="coerce")
        price_text = f"${price:,.0f}" if not pd.isna(price) else "Unavailable"
        context_blocks.append(
            f"""
Property {number}
Address: {house.get('streetAddress', 'Address unavailable')}
Price: {price_text}
Bedrooms: {house.get('numOfBedrooms', 'Not listed')}
Bathrooms: {house.get('numOfBathrooms', 'Not listed')}
Description: {str(house.get('description', ''))[:900]}
Retrieval relevance score: {score:.3f}
""".strip()
        )

    context = "\n\n".join(context_blocks)
    property_count = len(matches)

    prompt = f"""
You are a helpful AI real estate assistant helping users explore
historical Austin housing data.

User request:
{question}

The following are the ONLY properties you may recommend:
{context}

STRICT RULES:
1. Recommend no more than {property_count} properties, using only the properties
   supplied in the context.
2. Never invent an address, price, property feature, or listing.
3. Use the exact address and price from the context.
4. Briefly explain why each property matches the user's request.
5. Include a short exact quote from each property's description as evidence.
6. If a requested feature is not explicitly supported by the description, say:
   "This feature is not confirmed in the description."
7. A large lot or corner lot does NOT automatically mean a large backyard.
8. These are historical listings, not verified active listings.
9. Keep the response clear, concise, and professional.
10. If fewer than three properties are supplied, recommend only those supplied.

Format the response in Markdown with a numbered list. For each property use:
**[Address] — [Price]**
- **Why it matches:** ...
- **Description evidence:** "..."
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=120,
    )
    response.raise_for_status()

    result = response.json().get("response", "").strip()
    if not result:
        raise RuntimeError("Ollama returned an empty response.")

    return result


if __name__ == "__main__":
    user_question = input("What kind of house are you looking for? ")
    found = retrieve_houses(user_question)
    print("\nAI Recommendation:\n")
    print(generate_answer(user_question, matches=found))

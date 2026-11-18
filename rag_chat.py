
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load housing data and prepare descriptions
df = pd.read_csv("austinHousingData.csv")
df = df.dropna(subset=["description"]).copy()
df["description"] = df["description"].astype(str).str.strip()
df = df[df["description"] != ""].reset_index(drop=True)
df = df[df["description"].str.len() >= 100].reset_index(drop=True)

# Create text retrieval index
vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
house_vectors = vectorizer.fit_transform(df["description"])



def retrieve_houses(question, top_k=3, max_price=None, min_bedrooms=None):
    query_vector = vectorizer.transform([question])
    scores = cosine_similarity(query_vector, house_vectors).flatten()

    ranked_indices = scores.argsort()[::-1]
    matches = []

    for i in ranked_indices:
        house = df.iloc[i]

        price = pd.to_numeric(house["latestPrice"], errors="coerce")
        bedrooms = pd.to_numeric(house["numOfBedrooms"], errors="coerce")

        if max_price is not None:
            if pd.isna(price) or price > max_price:
                continue

        if min_bedrooms is not None:
            if pd.isna(bedrooms) or bedrooms < min_bedrooms:
                continue

        matches.append((house, float(scores[i])))

        if len(matches) == top_k:
            break

    return matches




def generate_answer(question, max_price=None, min_bedrooms=None):
    matches = retrieve_houses(
        question,
        top_k=3,
        max_price=max_price,
        min_bedrooms=min_bedrooms
    )


    # Give the LLM only the retrieved property information
    context = ""

    for number, (house, score) in enumerate(matches, start=1):
        context += f"""
Property {number}
Address: {house['streetAddress']}
Price: ${house['latestPrice']:,.0f}
Bedrooms: {house['numOfBedrooms']}
Bathrooms: {house['numOfBathrooms']}
Description: {house['description'][:900]}
"""

    
    prompt = f"""
You are an AI real estate assistant helping users explore
historical Austin housing data.

User question:
{question}

Here are the ONLY properties you can recommend:
{context}

STRICT RULES:
1. Recommend exactly 3 properties, numbered 1, 2, and 3.
2. Only use properties listed in the provided context.
3. Use the exact address and price from the context.
4. Explain briefly why each property matches the user's request.
5. Do not invent features or claim a property has something
   unless the description explicitly supports it.
6. If a requested feature is not confirmed, say so.
7. Do not recommend additional properties.
8. Keep the response clear, concise, and professional.
9. These are historical listings, not verified active listings.
10. For each property, include a short, exact quote from its
    description supporting the recommendation.
11. A large lot or corner lot does NOT automatically mean
    a large backyard. Never assume a feature is present.
12. If a requested feature is not explicitly confirmed,
    say "This feature is not confirmed in the description."

Format:

1. Property address - Price
   Why it matches: Brief explanation.

2. Property address - Price
   Why it matches: Brief explanation.

3. Property address - Price
   Why it matches: Brief explanation.
"""


    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma3:1b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        },
        timeout=120
    )
    response.raise_for_status()

    return response.json()["response"]


if __name__ == "__main__":
    question = input("What kind of house are you looking for? ")
    print("\nAI Recommendation:\n")
    print(generate_answer(question))

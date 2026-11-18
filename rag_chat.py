
"""TF-IDF property retrieval and Ollama-based recommendation generation."""

import re
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

vectorizer = TfidfVectorizer(
    stop_words="english",
    max_features=20000,
)
house_vectors = vectorizer.fit_transform(df["description"])


def extract_search_constraints(question):
    """
    Extract maximum price and minimum bedrooms from a user's message.

    Returns:
        {
            "max_price": float or None,
            "min_bedrooms": int or None
        }
    """

    text = question.lower()

    max_price = None
    min_bedrooms = None

    # Identify prices expressed with a qualifier, such as:
    # under $500,000, budget of 500k, or max price 450000.
    price_patterns = [
        r"\b(?:under|below|less than|up to|no more than|at most|"
        r"max(?:imum)?(?: price)?|budget(?: of| is)?|price(?: of)?)"
        r"\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\s*([km])?\b",

        # Explicit dollar amounts, such as $500,000 or $500k.
        r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*([km])?\b",

        # Shorthand amounts followed by k or m, such as 500k max.
        r"\b(\d+(?:\.\d+)?)\s*([km])\s*"
        r"(?:or less|maximum|max|budget)?\b",
    ]

    for pattern in price_patterns:
        match = re.search(pattern, text)

        if match:
            amount = float(match.group(1).replace(",", ""))
            suffix = (match.group(2) or "").lower()

            if suffix == "k":
                amount *= 1_000
            elif suffix == "m":
                amount *= 1_000_000

            max_price = amount
            break

    # Identify bedroom requirements, including:
    # 3 bedrooms, 3+ bedrooms, at least 3 bedrooms, and 3br.
    bedroom_pattern = (
        r"\b(?:(?:at least|minimum|min\.?|more than|over)\s*)?"
        r"(\d+)\s*\+?\s*(?:bed(?:room)?s?|br)\b"
    )

    bedroom_match = re.search(bedroom_pattern, text)

    if bedroom_match:
        min_bedrooms = int(bedroom_match.group(1))

        # "More than 3 bedrooms" means at least 4.
        if re.search(r"\b(?:more than|over)\s+\d+", text):
            min_bedrooms += 1

    return {
        "max_price": max_price,
        "min_bedrooms": min_bedrooms,
    }


def retrieve_houses(
    question,
    top_k=3,
    max_price=None,
    min_bedrooms=None,
):
    """Return the highest-scoring properties that satisfy numeric filters."""

    query_vector = vectorizer.transform([question])
    scores = cosine_similarity(query_vector, house_vectors).flatten()
    ranked_indices = scores.argsort()[::-1]

    matches = []

    for index in ranked_indices:
        house = df.iloc[index]

        price = pd.to_numeric(
            house.get("latestPrice"),
            errors="coerce",
        )
        bedrooms = pd.to_numeric(
            house.get("numOfBedrooms"),
            errors="coerce",
        )

        if max_price is not None:
            if pd.isna(price) or price > max_price:
                continue

        if min_bedrooms is not None:
            if pd.isna(bedrooms) or bedrooms < min_bedrooms:
                continue

        matches.append((house, float(scores[index])))

        if len(matches) >= top_k:
            break

    return matches


def generate_answer(
    question,
    matches=None,
    max_price=None,
    min_bedrooms=None,
):
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
        price = pd.to_numeric(
            house.get("latestPrice"),
            errors="coerce",
        )

        price_text = (
            f"${price:,.0f}"
            if not pd.isna(price)
            else "Unavailable"
        )

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


def classify_intent(question, conversation_history=None):
    """
    Decide whether the user wants a housing search or normal conversation.

    If classification fails, default to conversation rather than
    unexpectedly searching the housing dataset.
    """

    history = ""
    if conversation_history:
        history = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in conversation_history[-6:]
        )

    prompt = f"""
You are the intent router for an Austin real estate assistant.

Decide which of these two actions the user wants:

HOUSING_SEARCH:
The user wants to find, discover, recommend, compare, or filter
specific homes or properties. This includes requests involving
price, bedrooms, bathrooms, square footage, neighborhoods,
property features, or matching listings.

CONVERSATION:
The user wants a normal conversational response. This includes
general knowledge questions, explanations about mortgages,
real estate concepts, financial questions, greetings, unrelated
topics, and follow-up questions that do not request property
recommendations or a property search.

Important:
- Do not classify a question as HOUSING_SEARCH merely because it
  mentions a house, home, mortgage, price, or real estate.
- "What is a mortgage?" is CONVERSATION.
- "How much should I spend on a house?" is CONVERSATION unless
  the user asks you to find properties.
- "Find me a house under $500,000" is HOUSING_SEARCH.
- "Show me three-bedroom homes in Austin" is HOUSING_SEARCH.
- When uncertain, choose CONVERSATION.

Recent conversation:
{history}

Latest user message:
{question}

Return exactly one label:
HOUSING_SEARCH
or
CONVERSATION
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=60,
        )
        response.raise_for_status()

        result = response.json().get("response", "").strip().upper()

        if "HOUSING_SEARCH" in result:
            return "housing_search"

        return "conversation"

    except requests.RequestException:
        # Avoid an accidental housing search if intent detection fails.
        return "conversation"


def generate_conversation_answer(question, conversation_history=None):
    """Generate a normal conversational answer without housing retrieval."""

    history = ""
    if conversation_history:
        history = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in conversation_history[-8:]
        )

    prompt = f"""
You are a helpful, friendly, and knowledgeable AI assistant.

You are also capable of helping users explore Austin housing data,
but only use housing search when the user explicitly requests
property recommendations or a property search.

For this response, answer the user's message as a normal conversational
assistant. Do not search for properties or invent property listings.

Maintain continuity with the recent conversation when relevant.
Be clear, natural, and helpful. If the user asks an unrelated question,
answer it normally.

Recent conversation:
{history}

Latest user message:
{question}

Your response:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.5},
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

    constraints = extract_search_constraints(user_question)

    found = retrieve_houses(
        user_question,
        max_price=constraints["max_price"],
        min_bedrooms=constraints["min_bedrooms"],
    )

    print("\nDetected filters:", constraints)
    print("\nAI Recommendation:\n")
    print(generate_answer(user_question, matches=found))


import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load the Austin housing dataset
df = pd.read_csv("austinHousingData.csv")

# Keep houses with descriptions
df = df.dropna(subset=["description"]).copy()
df["description"] = df["description"].str.strip()
df = df[df["description"] != ""].reset_index(drop=True)

# Convert property descriptions into TF-IDF vectors
vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
house_vectors = vectorizer.fit_transform(df["description"])

# Example user search
query = input("Describe the house you are looking for: ")

# Compare the query with property descriptions
query_vector = vectorizer.transform([query])
scores = cosine_similarity(query_vector, house_vectors).flatten()

# Get the 5 highest-scoring properties
top_indices = scores.argsort()[::-1][:5]

print("Search:", query)

for rank, idx in enumerate(top_indices, start=1):
    house = df.iloc[idx]

    print(f"\nHouse {rank}")
    print("Address:", house["streetAddress"])
    print("Price:", house["latestPrice"])
    print("Bedrooms:", house["numOfBedrooms"])
    print("Relevance score:", round(float(scores[idx]), 3))
    print("Description:", house["description"][:300])

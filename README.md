
# Austin Real Estate AI Assistant

## Project Overview
This project uses text mining, information retrieval, and an LLM to help users find properties based on natural-language preferences.

The application uses historical Austin housing data and runs through Streamlit.

## Technologies
- Python
- Streamlit
- Pandas
- TF-IDF and Cosine Similarity
- Ollama (Gemma 3 1B)

## Dataset
austinHousingData.csv

The original dataset contains 15,171 housing records. The retrieval system uses property descriptions containing at least 100 characters.

## How It Works
1. The user enters housing preferences.
2. Price and bedroom filters are applied.
3. TF-IDF and cosine similarity rank relevant property descriptions.
4. The top three matching properties are sent to the LLM.
5. Ollama generates recommendations using the retrieved information.
6. Streamlit displays the AI response and original property descriptions.

## Setup (Mac)

Create a Python environment:

python3 -m venv .venv

Activate it:

source .venv/bin/activate

Install libraries:

python -m pip install -r requirements.txt

Install Ollama separately if needed, then download the model:

ollama pull gemma3:1b

Make sure Ollama is running.

## Run the Application

From the project folder:

python -m streamlit run app.py

Open http://localhost:8501

## Limitations
- The dataset contains historical housing records, not verified active listings.
- TF-IDF primarily measures lexical similarity.
- LLM-generated explanations may not always be fully supported by the property descriptions.

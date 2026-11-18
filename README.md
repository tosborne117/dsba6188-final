# Austin Real Estate AI Assistant

A Streamlit-based housing search assistant that uses TF-IDF retrieval and a
local Ollama model to recommend properties from a historical Austin housing
dataset. The interface uses a floating chatbot panel, a fixed image launcher,
and a full-page background.

> **Data note:** The dataset contains historical property records. Listings are
> not verified as currently available for sale.

## Features

- Natural-language home searches.
- TF-IDF and cosine-similarity ranking of property descriptions.
- Optional maximum-price and minimum-bedroom filters in the sidebar.
- Ollama (Gemma 3 1B) generates recommendations grounded in retrieved records.
- Chat-style user and assistant messages, with property details in expandable
  cards.
- Responsive floating chatbot window with background and launcher artwork.

## How it works

1. The user opens the chatbot using the fixed launcher image.
2. The user describes a preferred home in natural language.
3. Optional price and bedroom filters are applied.
4. TF-IDF and cosine similarity rank matching property descriptions.
5. The top three matching properties are supplied to the local Ollama model.
6. The model generates concise, evidence-based recommendations.
7. Streamlit displays the conversation and the original retrieved property
   descriptions.

The assistant is instructed to use only retrieved properties, preserve the
addresses and prices supplied to it, quote supporting description text, and
avoid claiming that unconfirmed features are present.

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit application, sidebar filters, chatbot conversation, and property display |
| `rag_chat.py` | TF-IDF retrieval and Ollama recommendation generation |
| `retrieval.py` | Standalone command-line retrieval experiment |
| `ui.py` | Background, floating chat panel, launcher, and responsive styling |
| `austinHousingData.csv` | Historical Austin housing dataset |
| `requirements.txt` | Python dependencies |

The background and chatbot launcher images are reused from the repository's
`main/static/` directory through their raw GitHub URLs. Keep those files in
the main branch at:

- `static/background.png`
- `static/chatbot-image.png`

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Install [Ollama](https://ollama.com/) separately, start the Ollama service,
and download the model:

```bash
ollama pull gemma3:1b
```

The application sends generation requests to
`http://localhost:11434/api/generate`. If Ollama is running elsewhere or a
different model is installed, update `OLLAMA_URL` or `OLLAMA_MODEL` in
`rag_chat.py`.

## Run the application

From the project directory:

```bash
python -m streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501).

## Limitations

- The dataset contains historical housing records, not verified active listings.
- TF-IDF primarily measures lexical similarity and may miss semantic matches.
- Recommendations depend on the information present in each property
  description.
- LLM-generated explanations should be checked against the original property
  description shown in each expandable result.
- The background and launcher artwork are loaded from the public `main`
  branch, so the app needs internet access to display those images.

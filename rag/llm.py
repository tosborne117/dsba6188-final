"""Chat models and embeddings from two providers: Ollama (local) and Google AI Studio."""

from langchain_core.embeddings import Embeddings

from rag import config


def list_chat_models(provider):
    """Return the chat models that can call tools. The agent needs tool calling."""
    if provider == config.OLLAMA:
        import ollama

        client = ollama.Client(host=config.OLLAMA_BASE_URL)
        models = []
        for m in client.list().models:
            caps = client.show(m.model).capabilities or []
            if "tools" in caps:
                models.append(m.model)
        return sorted(models)

    from google import genai

    # Gemma models on AI Studio do not support tool calling, so keep Gemini only
    client = genai.Client(api_key=config.get("GOOGLE_API_KEY"))
    return sorted(
        m.name.removeprefix("models/")
        for m in client.models.list()
        if "generateContent" in (m.supported_actions or []) and "gemini" in m.name
    )


def chat_model(provider, model_name, temperature):
    if provider == config.OLLAMA:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model_name, temperature=temperature, base_url=config.OLLAMA_BASE_URL
        )

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=config.get("GOOGLE_API_KEY"),
    )


class NomicPrefixEmbeddings(Embeddings):
    """nomic-embed-text was trained with task prefixes. Search works better with them."""

    def __init__(self, base):
        self.base = base

    def embed_documents(self, texts):
        return self.base.embed_documents([f"search_document: {t}" for t in texts])

    def embed_query(self, text):
        return self.base.embed_query(f"search_query: {text}")


def embeddings(provider):
    model = config.EMBED_MODEL[provider]
    if provider == config.OLLAMA:
        from langchain_ollama import OllamaEmbeddings

        base = OllamaEmbeddings(model=model, base_url=config.OLLAMA_BASE_URL)
        return NomicPrefixEmbeddings(base) if "nomic" in model else base

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=model,
        output_dimensionality=config.EMBED_DIM[provider],
        google_api_key=config.get("GOOGLE_API_KEY"),
    )

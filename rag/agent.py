"""Combined RAG and Snowflake text-to-SQL agent."""

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from rag import llm
from rag.text_to_sql import build_sql_tools


SYSTEM_PROMPT = """You are a helpful analytical assistant for DSBA 6188.

You can use two information sources:

1. Uploaded PDF documents:
   - search_documents: searches document content.
   - list_documents: lists uploaded documents and chunk counts.

2. Snowflake analytical data:
   - snowflake_table_lookup: discovers available SQL tables.
   - snowflake_column_lookup: discovers table columns and data types.
   - snowflake_execute_sql: executes validated read-only SQL.

Tool selection rules:

DOCUMENT QUESTIONS:
- For questions about which or how many documents exist, call list_documents.
- For questions about document content, call search_documents.
- Cite document facts using (source, page N).

SQL QUESTIONS:
- For analytical questions about customers, orders, sales, suppliers,
  regions, or other structured data, use Snowflake.
- Call snowflake_table_lookup when you need to discover available tables.
- Call snowflake_column_lookup before writing a query when you need
  to understand a table's columns.
- Generate SQL using only the discovered tables and columns.
- Execute SQL using snowflake_execute_sql.
- Explain the results using the returned data.
- Never invent query results.

COMBINED QUESTIONS:
- If a question requires both uploaded documents and analytical data,
  use both sets of tools.
- Clearly distinguish document findings from SQL findings.

GENERAL QUESTIONS:
- Greetings and general questions that do not require either data source
  can be answered directly.

IMPORTANT:
- Never claim to have queried Snowflake unless you called the SQL tools.
- Never invent tables, columns, or query results.
- Only use the available tools and their returned results.
- SQL execution is read-only.
"""


def build_agent(
    provider,
    model_name,
    temperature,
    store,
    top_k,
    get_sources=None,
    sql_conn=None,
    use_sql=False,
):
    """Build the agent with whichever information sources are enabled."""

    @tool
    def search_documents(query: str) -> str:
        """Search the uploaded PDF documents.

        Args:
            query: What to look for, written as a short search phrase.
        """
        results = store.similarity_search_with_score(query, k=top_k)

        if not results:
            return "No matching document chunks found."

        return "\n\n---\n\n".join(
            f"[source: {doc.metadata.get('source')}, "
            f"page {doc.metadata.get('page')}, score {score:.3f}]\n"
            f"{doc.page_content}"
            for doc, score in results
        )

    @tool
    def list_documents() -> str:
        """List all uploaded documents and their chunk counts."""
        sources = get_sources()

        if not sources:
            return "The document library is empty."

        lines = [
            f"- {name}: {count} chunks"
            for name, count in sources.items()
        ]

        return (
            f"{len(sources)} documents, "
            f"{sum(sources.values())} chunks:\n"
            + "\n".join(lines)
        )

    tools = []

    if store:
        tools.append(search_documents)

    if get_sources:
        tools.append(list_documents)

    if use_sql and sql_conn:
        tools.extend(build_sql_tools(sql_conn))

    return create_react_agent(
        llm.chat_model(provider, model_name, temperature),
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
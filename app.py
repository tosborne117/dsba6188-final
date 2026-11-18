
"""Austin Real Estate AI Assistant with a floating chatbot interface."""

import re

import streamlit as st

from rag_chat import (
    classify_intent,
    generate_conversation_answer,
    generate_answer,
    retrieve_houses,
)
from ui import apply_chat_theme


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Austin Real Estate AI",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

chat_open = apply_chat_theme()

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------
# Extract price and bedroom requirements from user messages
# ---------------------------------------------------------

def extract_search_constraints(question):
    """Extract a maximum price and minimum bedroom count."""

    question = question.lower().replace(",", "")

    max_price = None
    min_bedrooms = None

    # Examples:
    # under $500,000
    # budget of 450k
    # 500k max
    # no more than 600000
    price_pattern = (
        r"(?:under|below|less than|no more than|at most|"
        r"maximum(?: price)?(?: of)?|budget(?: of)?|up to)"
        r"\s*\$?(\d+(?:\.\d+)?)\s*(k|m)?"
        r"|"
        r"\$?(\d+(?:\.\d+)?)\s*(k|m)?\s*(?:max|maximum)"
    )

    price_match = re.search(price_pattern, question)

    if price_match:
        if price_match.group(1) is not None:
            amount = float(price_match.group(1))
            suffix = price_match.group(2)
        else:
            amount = float(price_match.group(3))
            suffix = price_match.group(4)

        if suffix == "k":
            amount *= 1_000
        elif suffix == "m":
            amount *= 1_000_000

        max_price = amount

    # Examples:
    # at least 3 bedrooms
    # 3+ bedrooms
    # 3 bedroom
    # 3br
    bedroom_patterns = [
        r"(?:at least|minimum of|min(?:imum)?)\s*(\d+)\s*(?:bedrooms?|br)\b",
        r"(\d+)\s*\+\s*(?:bedrooms?|br)\b",
        r"(\d+)\s*(?:bedrooms?|br)\b",
    ]

    for pattern in bedroom_patterns:
        bedroom_match = re.search(pattern, question)

        if bedroom_match:
            min_bedrooms = int(bedroom_match.group(1))
            break

    return {
        "max_price": max_price,
        "min_bedrooms": min_bedrooms,
    }


# ---------------------------------------------------------
# Sidebar search preferences
# ---------------------------------------------------------

with st.sidebar:
    st.header("Search preferences")

    max_price = st.number_input(
        "Maximum price ($)",
        min_value=0,
        value=0,
        step=25000,
        help="Enter 0 for no price limit.",
    )

    min_bedrooms = st.number_input(
        "Minimum bedrooms",
        min_value=0,
        value=0,
        step=1,
        help="Enter 0 for no bedroom requirement.",
    )

    st.divider()

    st.caption("These filters apply to every property search.")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------
# Only display the chatbot panel when it is open
# ---------------------------------------------------------

if not chat_open:
    st.stop()


# ---------------------------------------------------------
# Chatbot panel
# ---------------------------------------------------------

with st.container(key="chat_window"):

    # Header
    st.markdown(
        '<div class="assistant-heading">Erica - Virtual Assistant</div>'
        '<div class="assistant-subheading">'
        'Ask about homes, features, and your search preferences.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Reserve a location for the conversation history.
    # The input form will appear immediately below it.
    history_slot = st.empty()

    # -----------------------------------------------------
    # Message input
    # -----------------------------------------------------

    with st.form(
        "housing_chat_form",
        clear_on_submit=True,
    ):

        input_col, submit_col = st.columns(
            [5, 1],
            vertical_alignment="bottom",
        )

        with input_col:
            prompt = st.text_input(
                "Message",
                placeholder=(
                    "e.g. Find a home with a renovated kitchen "
                    "and backyard..."
                ),
                label_visibility="collapsed",
            )

        with submit_col:
            submitted = st.form_submit_button(
                "Send",
                use_container_width=True,
            )

    # -----------------------------------------------------
    # Conversation history display
    # -----------------------------------------------------

    def render_history(show_thinking=False):
        """Render messages and optionally show a Thinking indicator."""

        with history_slot.container():

            with st.container(height=470, key="chat_history"):

                # Initial welcome message
                if not st.session_state.messages:
                    with st.chat_message("assistant", avatar="🏡"):
                        st.markdown(
                            "Welcome! I'm your Austin real estate assistant. "
                            "Tell me what you're looking for—for example, a "
                            "home with a renovated kitchen, an open floor "
                            "plan, or a large backyard."
                        )

                # Display existing conversation
                for message in st.session_state.messages:

                    avatar = (
                        "🧑"
                        if message["role"] == "user"
                        else "🏡"
                    )

                    with st.chat_message(
                        message["role"],
                        avatar=avatar,
                    ):

                        st.markdown(message["content"])

                        # Display property details below assistant responses
                        if message["role"] == "assistant":

                            for index, listing in enumerate(
                                message.get("listings", []),
                                start=1,
                            ):

                                price_text = (
                                    f"${listing['price']:,.0f}"
                                    if listing["price"] is not None
                                    else "Price unavailable"
                                )

                                with st.expander(
                                    f"{index}. {listing['address']} — {price_text}"
                                ):

                                    st.write(
                                        f"**Bedrooms:** {listing['bedrooms']}"
                                    )

                                    st.write(
                                        f"**Bathrooms:** {listing['bathrooms']}"
                                    )

                                    st.write(
                                        f"**Relevance score:** "
                                        f"{listing['score']:.3f}"
                                    )

                                    st.write(
                                        "**Original property description:**"
                                    )

                                    st.write(listing["description"])

                # Temporary assistant response while Ollama works
                if show_thinking:
                    with st.chat_message("assistant", avatar="🏡"):
                        st.markdown("**Thinking...**")

    # -----------------------------------------------------
    # Process submitted messages
    # -----------------------------------------------------

    if submitted and prompt.strip():

        user_question = prompt.strip()

        # Save the user's message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_question,
            }
        )

        # Display the user's message and Thinking indicator
        # before running the model.
        render_history(show_thinking=True)

        try:

            # Determine whether the user wants a property search
            # or a normal conversational response.
            intent = classify_intent(
                user_question,
                conversation_history=st.session_state.messages[:-1],
            )

            # ---------------------------------------------
            # ROUTE 1: NORMAL CONVERSATION
            # ---------------------------------------------

            if intent == "conversation":

                answer = generate_conversation_answer(
                    user_question,
                    conversation_history=st.session_state.messages[:-1],
                )

                listings = []

            # ---------------------------------------------
            # ROUTE 2: HOUSING SEARCH
            # ---------------------------------------------

            else:

                detected_filters = extract_search_constraints(
                    user_question
                )

                detected_price = detected_filters["max_price"]
                detected_bedrooms = detected_filters["min_bedrooms"]

                sidebar_price = (
                    max_price if max_price > 0 else None
                )

                sidebar_bedrooms = (
                    min_bedrooms if min_bedrooms > 0 else None
                )

                # Apply the stricter price limit
                if detected_price is not None and sidebar_price is not None:
                    effective_max_price = min(
                        detected_price,
                        sidebar_price,
                    )
                else:
                    effective_max_price = (
                        detected_price
                        if detected_price is not None
                        else sidebar_price
                    )

                # Apply the stricter bedroom requirement
                if (
                    detected_bedrooms is not None
                    and sidebar_bedrooms is not None
                ):
                    effective_min_bedrooms = max(
                        detected_bedrooms,
                        sidebar_bedrooms,
                    )
                else:
                    effective_min_bedrooms = (
                        detected_bedrooms
                        if detected_bedrooms is not None
                        else sidebar_bedrooms
                    )

                # Retrieve matching properties
                matches = retrieve_houses(
                    user_question,
                    top_k=3,
                    max_price=effective_max_price,
                    min_bedrooms=effective_min_bedrooms,
                )

                if matches:

                    answer = generate_answer(
                        user_question,
                        matches=matches,
                    )

                    listings = []

                    for house, score in matches:

                        price = house.get("latestPrice")
                        bedrooms = house.get("numOfBedrooms")
                        bathrooms = house.get("numOfBathrooms")

                        # Convert price safely
                        try:
                            price = float(price)

                            if price != price:
                                price = None

                        except (TypeError, ValueError):
                            price = None

                        # Handle missing property information
                        if bedrooms is None or str(bedrooms) == "nan":
                            bedrooms = "N/A"

                        if bathrooms is None or str(bathrooms) == "nan":
                            bathrooms = "N/A"

                        listings.append(
                            {
                                "address": str(
                                    house.get(
                                        "streetAddress",
                                        "Address unavailable",
                                    )
                                ),
                                "price": price,
                                "bedrooms": str(bedrooms),
                                "bathrooms": str(bathrooms),
                                "description": str(
                                    house.get("description", "")
                                ),
                                "score": float(score),
                            }
                        )

                else:

                    answer = (
                        "I couldn't find properties matching those "
                        "preferences. Try adjusting your price or "
                        "bedroom requirements, or describing the "
                        "features differently."
                    )

                    listings = []

            # ---------------------------------------------
            # SAVE THE ASSISTANT RESPONSE
            # ---------------------------------------------

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "listings": listings,
                }
            )

        except Exception as error:

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "I ran into a problem while processing your request. "
                        f"Please try again. Details: {error}"
                    ),
                    "listings": [],
                }
            )

        # Refresh the chatbot to replace Thinking with the response
        st.rerun()

    else:

        # Display the existing conversation when no new message is submitted
        render_history()

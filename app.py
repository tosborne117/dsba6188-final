"""Austin Real Estate AI Assistant with a floating chatbot interface."""

import streamlit as st

from rag_chat import generate_answer, retrieve_houses
from ui import apply_chat_theme, close_assistant


st.set_page_config(
    page_title="Austin Real Estate AI",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

chat_open = apply_chat_theme()

if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown(
    """
    <div class="page-intro">
        <div class="page-kicker">AUSTIN REAL ESTATE</div>
        <h1>Find a home that fits your life.</h1>
        <p>Describe what matters to you and explore matching properties
        from our historical Austin housing dataset.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "This assistant uses historical housing data. Properties are not "
    "verified as currently for sale."
)

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

if not chat_open:
    st.stop()

# The fixed panel is rendered only while the launcher is open.
with st.container(key="chat_window"):
    header_col, close_col = st.columns([9, 1], vertical_alignment="center")

    with header_col:
        st.markdown(
            '<div class="assistant-heading">Austin Real Estate Assistant</div>'
            '<div class="assistant-subheading">'
            'Ask about homes, features, and your search preferences.'
            '</div>',
            unsafe_allow_html=True,
        )

    with close_col:
        if st.button("✕", key="close_chatbot", help="Close chatbot"):
            close_assistant()
            st.rerun()

    st.divider()

    # This placeholder reserves the conversation's position above the form.
    history_slot = st.empty()

    with st.form("housing_chat_form", clear_on_submit=True):
        prompt = st.text_input(
            "Message",
            placeholder="e.g. Find a home with a renovated kitchen and backyard...",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and prompt.strip():
        price_filter = max_price if max_price > 0 else None
        bedroom_filter = min_bedrooms if min_bedrooms > 0 else None

        st.session_state.messages.append(
            {"role": "user", "content": prompt.strip()}
        )

        try:
            with st.spinner("Searching properties and preparing recommendations..."):
                matches = retrieve_houses(
                    prompt.strip(),
                    top_k=3,
                    max_price=price_filter,
                    min_bedrooms=bedroom_filter,
                )

                if matches:
                    answer = generate_answer(
                        prompt.strip(),
                        matches=matches,
                    )
                    listings = []
                    for house, score in matches:
                        price = house.get("latestPrice")
                        bedrooms = house.get("numOfBedrooms")
                        bathrooms = house.get("numOfBathrooms")
                        listings.append(
                            {
                                "address": str(house.get("streetAddress", "Address unavailable")),
                                "price": float(price) if price is not None and str(price) != "nan" else None,
                                "bedrooms": str(bedrooms) if bedrooms is not None else "N/A",
                                "bathrooms": str(bathrooms) if bathrooms is not None else "N/A",
                                "description": str(house.get("description", "")),
                                "score": float(score),
                            }
                        )
                else:
                    answer = (
                        "I couldn't find properties matching those preferences. "
                        "Try increasing the maximum price, lowering the bedroom "
                        "minimum, or describing the features differently."
                    )
                    listings = []

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
                        "I ran into a problem while searching for properties. "
                        f"Please try again. Details: {error}"
                    ),
                    "listings": [],
                }
            )

        st.rerun()

    # Fill the placeholder after the form has been declared. Streamlit keeps
    # this content in the placeholder's earlier position, above the input.
    with history_slot.container():
        with st.container(height=470, key="chat_history"):
            if not st.session_state.messages:
                with st.chat_message("assistant", avatar="🏡"):
                    st.markdown(
                        "Welcome! I'm your Austin real estate assistant. "
                        "Tell me what you're looking for—for example, a home "
                        "with a renovated kitchen, an open floor plan, or a "
                        "large backyard."
                    )

            for message in st.session_state.messages:
                avatar = "🧑" if message["role"] == "user" else "🏡"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

                    if message["role"] == "assistant":
                        for index, listing in enumerate(
                            message.get("listings", []), start=1
                        ):
                            price_text = (
                                f"${listing['price']:,.0f}"
                                if listing["price"] is not None
                                else "Price unavailable"
                            )
                            with st.expander(
                                f"{index}. {listing['address']} — {price_text}"
                            ):
                                st.write(f"**Bedrooms:** {listing['bedrooms']}")
                                st.write(f"**Bathrooms:** {listing['bathrooms']}")
                                st.write(
                                    f"**Relevance score:** {listing['score']:.3f}"
                                )
                                st.write("**Original property description:**")
                                st.write(listing["description"])

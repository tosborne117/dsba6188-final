
import streamlit as st
from rag_chat import generate_answer, retrieve_houses

st.set_page_config(
    page_title="Austin Real Estate AI",
    page_icon="🏡",
    layout="wide"
)

st.title("🏡 Austin Real Estate AI Assistant")

st.write(
    "Find homes using natural language and AI-powered "
    "property recommendations."
)

st.info(
    "This application uses historical Austin housing data. "
    "Properties are not verified as currently for sale."
)

st.subheader("Search Preferences")

col1, col2 = st.columns(2)

with col1:
    max_price = st.number_input(
        "Maximum Price ($)",
        min_value=0,
        value=0,
        step=25000,
        help="Enter 0 for no price limit."
    )

with col2:
    min_bedrooms = st.number_input(
        "Minimum Bedrooms",
        min_value=0,
        value=0,
        step=1,
        help="Enter 0 for no bedroom requirement."
    )

question = st.text_area(
    "Describe your ideal home:",
    placeholder="Example: A home with a renovated kitchen and large backyard"
)

if st.button("Find My Home", type="primary"):

    if not question.strip():
        st.warning("Please describe what you're looking for.")

    else:
        price_filter = max_price if max_price > 0 else None
        bedroom_filter = min_bedrooms if min_bedrooms > 0 else None

        with st.spinner("Searching Austin homes and generating recommendations..."):
            try:
                matches = retrieve_houses(
                    question,
                    top_k=3,
                    max_price=price_filter,
                    min_bedrooms=bedroom_filter
                )

                if matches:
                    answer = generate_answer(
                        question,
                        max_price=price_filter,
                        min_bedrooms=bedroom_filter
                    )

            except Exception as error:
                st.error(f"Unable to generate recommendations: {error}")
                st.stop()

        if not matches:
            st.warning("No properties matched your filters. Try adjusting them.")
            st.stop()

        st.subheader("AI Recommendations")
        st.write(answer)

        st.subheader("Retrieved Property Listings")

        for rank, (house, score) in enumerate(matches, start=1):
            with st.expander(
                f"{rank}. {house['streetAddress']} - ${house['latestPrice']:,.0f}"
            ):
                st.write(f"**Bedrooms:** {house['numOfBedrooms']}")
                st.write(f"**Bathrooms:** {house['numOfBathrooms']}")
                st.write(f"**Relevance Score:** {score:.3f}")
                st.write("**Original Property Description:**")
                st.write(house["description"])

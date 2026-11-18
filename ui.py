"""Visual styling and floating chatbot launcher for the housing assistant."""

import streamlit as st


# The assets remain in the main branch, so the alt branch can reuse the exact
# same background and launcher artwork without duplicating binary files.
BACKGROUND_URL = (
    "https://raw.githubusercontent.com/tosborne117/dsba6188-final/"
    "main/static/background.png"
)
CHATBOT_IMAGE_URL = (
    "https://raw.githubusercontent.com/tosborne117/dsba6188-final/"
    "main/static/chatbot-image.png"
)


def apply_chat_theme():
    """Apply the background, floating chat panel, and fixed launcher."""
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("{BACKGROUND_URL}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        [data-testid="stHeader"] {{
            background: rgba(255, 255, 255, 0.15);
        }}

        [data-testid="stSidebar"] {{
            background: rgba(23, 23, 23, 0.96);
        }}

        [data-testid="stSidebar"] * {{
            color: #f5f5f5;
        }}

        .page-intro {{
            max-width: 780px;
            margin: 11vh auto 20px auto;
            padding: 30px 36px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.88);
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.13);
            text-align: center;
        }}

        .page-intro h1 {{
            color: #003366;
            font-size: clamp(2rem, 4vw, 3.2rem);
            margin: 8px 0 12px 0;
        }}

        .page-intro p {{
            color: #424b55;
            font-size: 1.05rem;
            margin-bottom: 0;
        }}

        .page-kicker {{
            color: #52708e;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.18em;
        }}

        /* Floating conversation panel */
        .st-key-chat_window {{
            position: fixed !important;
            bottom: 90px !important;
            right: 145px !important;
            width: 575px !important;
            height: 750px !important;
            max-width: calc(100vw - 30px) !important;
            max-height: calc(100vh - 120px) !important;
            box-sizing: border-box !important;
            overflow: hidden !important;
            padding: 22px !important;
            background: #ffffff !important;
            border: 1px solid #d5d5d5 !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28) !important;
            z-index: 999990 !important;
        }}

        .assistant-heading {{
            color: #003366;
            font-size: 21px;
            font-weight: 650;
            margin-bottom: 3px;
        }}

        .assistant-subheading {{
            color: #666666;
            font-size: 12px;
        }}

        .st-key-chat_history {{
            overflow-y: auto !important;
            overflow-x: hidden !important;
            background: #ffffff !important;
        }}

        .st-key-chat_history [data-testid="stChatMessage"] {{
            background: #eaeaea;
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 10px;
        }}

        .st-key-chat_history [data-testid="stChatMessage"]:has(
            [data-testid="chatAvatarIcon-user"]
        ) {{
            background: #003366;
            color: #ffffff;
        }}

        .st-key-chat_history [data-testid="stChatMessage"]:has(
            [data-testid="chatAvatarIcon-user"]
        ) p {{
            color: #ffffff !important;
        }}

        .st-key-chat_history [data-testid="stChatMessage"]:not(:has(
            [data-testid="chatAvatarIcon-user"]
        )) p {{
            color: #222222 !important;
        }}

        .st-key-chat_window [data-testid="stForm"] {{
            background: #ffffff !important;
            padding-top: 10px !important;
            padding-bottom: 0 !important;
            border-top: 1px solid #eeeeee !important;
            margin-top: 8px !important;
        }}

        .st-key-chat_window [data-testid="stTextInput"] input {{
            background: #eeeeee !important;
            color: #222222 !important;
            border: 1px solid #cccccc !important;
            border-radius: 8px !important;
            min-height: 42px;
        }}

        .st-key-chat_window [data-testid="stFormSubmitButton"] button {{
            background: #003366 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
        }}

        .st-key-chat_window [data-testid="stButton"] button {{
            border-radius: 8px;
        }}

        /* Fixed image launcher */
        .st-key-chatbot_toggle {{
            position: fixed !important;
            bottom: 40px !important;
            right: 45px !important;
            width: 110px !important;
            height: 110px !important;
            z-index: 999999 !important;
        }}

        .st-key-chatbot_toggle button {{
            width: 110px !important;
            height: 110px !important;
            min-height: 110px !important;
            padding: 0 !important;
            border: none !important;
            border-radius: 50% !important;
            background-image: url("{CHATBOT_IMAGE_URL}") !important;
            background-size: contain !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-color: transparent !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.30);
            color: transparent !important;
            font-size: 0 !important;
            cursor: pointer;
        }}

        .st-key-chatbot_toggle button:hover {{
            transform: scale(1.05);
            border: none !important;
        }}

        @media (max-width: 700px) {{
            .page-intro {{
                margin: 5vh 8px 16px 8px;
                padding: 22px 18px;
            }}

            .st-key-chat_window {{
                right: 10px !important;
                bottom: 85px !important;
                width: calc(100vw - 20px) !important;
                height: calc(100vh - 110px) !important;
                max-width: calc(100vw - 20px) !important;
                max-height: calc(100vh - 110px) !important;
                padding: 15px !important;
            }}

            .st-key-chatbot_toggle {{
                bottom: 15px !important;
                right: 15px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button(" ", key="chatbot_toggle", help="Open or close the assistant"):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

    return st.session_state.chat_open


def close_assistant():
    """Close the floating chatbot."""
    st.session_state.chat_open = False


"""Visual styling and floating chatbot launcher for the housing assistant."""

import base64
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

BACKGROUND_PATH = STATIC_DIR / "background.png"
CHATBOT_IMAGE_PATH = STATIC_DIR / "chatbot-image.png"


def load_image_as_base64(image_path):
    """Read a local image and return its Base64 representation."""
    if not image_path.exists():
        raise FileNotFoundError(
            f"Required image not found: {image_path}"
        )

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def apply_chat_theme():
    """Apply the background, floating chat panel, and launcher."""

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    background_image = load_image_as_base64(BACKGROUND_PATH)
    chatbot_image = load_image_as_base64(CHATBOT_IMAGE_PATH)

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image:
                url("data:image/png;base64,{background_image}");
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

        /* Floating chatbot panel */
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

        /* Conversation history: normal document flow */
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

        /* Input form stays after the history in normal flow.
           Reserve right-side space for the overlapping launcher. */
        .st-key-chat_window [data-testid="stForm"] {{
            width: calc(100% - 70px) !important;
            max-width: calc(100% - 70px) !important;
            background: #ffffff !important;
            padding: 10px 0 0 0 !important;
            border-top: 1px solid #eeeeee !important;
            margin-top: 8px !important;
        }}

        .st-key-chat_window [data-testid="stTextInput"] input {{
            background: #eeeeee !important;
            color: #222222 !important;
            border: 1px solid #cccccc !important;
            border-radius: 8px !important;
            min-height: 42px !important;
        }}

        .st-key-chat_window [data-testid="stFormSubmitButton"] button {{
            background: #003366 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            min-height: 42px !important;
            white-space: nowrap !important;
        }}

        .st-key-chat_window [data-testid="stButton"] button {{
            border-radius: 8px;
        }}

        /* Launcher shifted left by 35 pixels */
        .st-key-chatbot_toggle {{
            position: fixed !important;
            bottom: 40px !important;
            right: 115px !important;
            width: 110px !important;
            height: 110px !important;
            #transform: translateX(-35px) !important;
            z-index: 999999 !important;
        }}

        .st-key-chatbot_toggle button {{
            width: 110px !important;
            height: 110px !important;
            min-height: 110px !important;
            padding: 0 !important;
            border: none !important;
            border-radius: 50% !important;
            background-image:
                url("data:image/png;base64,{chatbot_image}") !important;
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
            border: none !important;
            filter: brightness(1.05);
        }}

        @media (max-width: 700px) {{
            .st-key-chat_window {{
                right: 10px !important;
                bottom: 145px !important;
                width: calc(100vw - 20px) !important;
                height: calc(100vh - 170px) !important;
                max-width: calc(100vw - 20px) !important;
                max-height: calc(100vh - 170px) !important;
                padding: 15px !important;
            }}

            .st-key-chat_window [data-testid="stForm"] {{
                width: 100% !important;
                max-width: 100% !important;
            }}

            .st-key-chatbot_toggle {{
                bottom: 15px !important;
                right: 50px !important;
                transform: translateX(-35px) !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        " ",
        key="chatbot_toggle",
        help="Open or close the assistant",
    ):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

    return st.session_state.chat_open


def close_assistant():
    """Close the floating chatbot."""
    st.session_state.chat_open = False

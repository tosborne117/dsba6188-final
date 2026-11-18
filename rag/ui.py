
"""Visual styling and floating chatbot launcher."""

import base64
from pathlib import Path

import streamlit as st


APP_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_DIR / "static"


def find_image(name):
    """Find an image in the static directory."""

    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = STATIC_DIR / f"{name}{ext}"

        if path.exists():
            return path

    return None


def image_uri(name):
    """Convert a local image into a base64 data URI."""

    path = find_image(name)

    if path is None:
        return None

    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }[path.suffix.lower()]

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")

    return f"data:{mime};base64,{encoded}"


def apply_chat_theme():
    """Apply the background, floating chat panel, and fixed launcher."""

    background = image_uri("background")
    chatbot_image = image_uri("chatbot-image")

    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    # Background
    if background:
        background_css = f"""
            background-image: url("{background}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        """
    else:
        background_css = "background: #dce5ef;"

    # Launcher image
    launcher_css = (
        f'background-image: url("{chatbot_image}");'
        if chatbot_image
        else "background: #003366;"
    )

    st.markdown(
        f"""
        <style>

        /* Application background */
        [data-testid="stAppViewContainer"] {{
            {background_css}
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: #171717;
        }}

        /* ---------------------------------------------
           FLOATING CHAT WINDOW
           --------------------------------------------- */

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

            box-shadow: 0 8px 28px rgba(0,0,0,.28) !important;

            z-index: 999990 !important;
        }}

        /* Chat heading */
        .assistant-heading {{
            color: #003366;
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 5px;
        }}

        .assistant-subheading {{
            color: #666666;
            font-size: 13px;
            margin-bottom: 12px;
        }}

        /* ---------------------------------------------
           SCROLLABLE CONVERSATION HISTORY
           --------------------------------------------- */

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

        /* User messages */
        .st-key-chat_history [data-testid="stChatMessage"]:has(
            [data-testid="chatAvatarIcon-user"]
        ) {{
            background: #003366;
            color: white;
        }}

        .st-key-chat_history [data-testid="stChatMessage"]:has(
            [data-testid="chatAvatarIcon-user"]
        ) p {{
            color: white !important;
        }}

        /* Assistant response text */
        .st-key-chat_history [data-testid="stChatMessage"]:not(:has(
            [data-testid="chatAvatarIcon-user"]
        )) p {{
            color: #222222 !important;
        }}

        /* ---------------------------------------------
           INPUT AREA
           --------------------------------------------- */

        .st-key-chat_window [data-testid="stForm"] {{
            background: #ffffff !important;

            padding-top: 10px !important;
            padding-bottom: 0 !important;

            border-top: 1px solid #eeeeee !important;

            margin-top: 8px !important;
        }}

        /* Input field */
        .st-key-chat_window [data-testid="stTextInput"] input {{
            background: #eeeeee !important;
            color: #222222 !important;

            border: 1px solid #cccccc !important;
            border-radius: 8px !important;

            min-height: 42px;
        }}

        /* Send button */
        .st-key-chat_window [data-testid="stFormSubmitButton"] button {{
            background: #003366 !important;
            color: white !important;

            border: none !important;
            border-radius: 8px !important;
        }}

        /* Close button */
        .st-key-chat_window [data-testid="stButton"] button {{
            border-radius: 8px;
        }}

        /* ---------------------------------------------
           FIXED CHATBOT LAUNCHER
           --------------------------------------------- */

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

            {launcher_css}

            background-size: contain !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-color: transparent !important;

            box-shadow: 0 4px 14px rgba(0,0,0,.30);

            color: transparent !important;
            font-size: 0 !important;

            cursor: pointer;
        }}

        .st-key-chatbot_toggle button:hover {{
            transform: scale(1.05);
            border: none !important;
        }}

        /* ---------------------------------------------
           RESPONSIVE LAYOUT
           --------------------------------------------- */

        @media (max-width: 700px) {{

            .st-key-chat_window {{
                right: 10px !important;
                bottom: 85px !important;

                width: calc(100vw - 20px) !important;
                height: calc(100vh - 110px) !important;

                max-width: calc(100vw - 20px) !important;
                max-height: calc(100vh - 110px) !important;

                padding: 15px !important;
            }}

            .st-key-chat_history {{
                max-height: calc(100vh - 300px) !important;
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

    # Chatbot launcher
    if st.button(" ", key="chatbot_toggle"):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

    return st.session_state.chat_open


def close_assistant():
    """Close the floating chatbot without changing launcher position."""

    st.session_state.chat_open = False

import os
import base64
import streamlit as st
from google import genai
from google.genai import types

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(page_title="AI Interior Designer", layout="wide")
st.title("🏡 AI Interior Design Assistant")

# ================================
# 🔐 API KEY INPUT
# ================================
api_key = st.text_input("Enter your Gemini API Key", type="password")

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key to continue")
    st.stop()

# Initialize client AFTER key is entered
client = genai.Client(api_key=api_key)

# ================================
# SESSION STATE
# ================================
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = []

if "last_image" not in st.session_state:
    st.session_state.last_image = None


# ================================
# INTENT DETECTION
# ================================
def detect_intent(msg: str):
    msg = msg.lower()

    generate_words = ["generate", "create", "design", "make"]
    edit_words = ["change", "edit", "modify", "replace", "remove", "add"]
    zoom_words = ["zoom", "focus", "crop", "highlight"]

    if any(w in msg for w in generate_words):
        return "generate"

    if any(w in msg for w in edit_words):
        return "edit"

    if any(w in msg for w in zoom_words):
        return "zoom"

    return "question"


# ================================
# IMAGE GENERATION
# ================================
def generate_image(prompt):
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        for part in res.candidates[0].content.parts:
            if part.inline_data:
                data = part.inline_data.data

                if isinstance(data, bytes):
                    data = base64.b64encode(data).decode()

                return f"data:image/png;base64,{data}"

    except Exception as e:
        st.error(f"Generate Error: {e}")

    return None


# ================================
# IMAGE EDIT / ZOOM
# ================================
def edit_image(prompt, base64_image):
    try:
        header, encoded = base64_image.split(",", 1)
        image_bytes = base64.b64decode(encoded)

        res = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": image_bytes
                    }
                }
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        if not res.candidates:
            return None

        parts = res.candidates[0].content.parts or []

        for part in parts:
            if part.inline_data:
                data = part.inline_data.data

                if isinstance(data, bytes):
                    data = base64.b64encode(data).decode()

                return f"data:image/png;base64,{data}"

    except Exception as e:
        st.error(f"Edit Error: {e}")

    return None


# ================================
# CHAT FUNCTION
# ================================
def chat_with_ai(msg):
    try:
        history = st.session_state.chat_memory[-5:]

        context = ""
        for h in history:
            context += f"User: {h['user']}\nAssistant: {h['bot']}\n"

        context += f"User: {msg}\nAssistant:"

        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
You are a smart interior design assistant.

Conversation:
{context}

Reply naturally like a human.
"""
        )

        return res.text

    except Exception as e:
        return "Something went wrong"


# ================================
# DISPLAY CHAT
# ================================
for chat in st.session_state.chat_memory:
    with st.chat_message("user"):
        st.write(chat["user"])

    with st.chat_message("assistant"):
        st.write(chat["bot"])
        if chat.get("image"):
            st.image(chat["image"], use_container_width=True)


# ================================
# INPUT
# ================================
user_input = st.chat_input("Ask, design, edit, or zoom...")

if user_input:
    intent = detect_intent(user_input)

    with st.chat_message("user"):
        st.write(user_input)

    # ============================
    # GENERATE
    # ============================
    if intent == "generate":
        with st.chat_message("assistant"):
            with st.spinner("Generating design..."):

                prompt = f"""
A photorealistic interior design of {user_input}.
Modern style, ultra detailed, 4K, cinematic lighting.
"""

                image = generate_image(prompt)

                if image:
                    st.image(image)
                    st.session_state.last_image = image

                    st.session_state.chat_memory.append({
                        "user": user_input,
                        "bot": "Generated design",
                        "image": image
                    })
                else:
                    st.write("❌ Failed to generate image")

    # ============================
    # EDIT
    # ============================
    elif intent == "edit" and st.session_state.last_image:
        with st.chat_message("assistant"):
            with st.spinner("Editing image..."):

                prompt = f"""
You are a professional interior image editor.

User request: {user_input}

STRICT RULES:
- Keep SAME layout
- Keep SAME camera angle
- Keep SAME lighting
- ONLY modify requested object

Return ultra realistic image.
"""

                image = edit_image(prompt, st.session_state.last_image)

                if image:
                    st.image(image)
                    st.session_state.last_image = image

                    st.session_state.chat_memory.append({
                        "user": user_input,
                        "bot": "Edited image",
                        "image": image
                    })
                else:
                    st.write("⚠️ Edit failed")

    # ============================
    # ZOOM
    # ============================
    elif intent == "zoom" and st.session_state.last_image:
        with st.chat_message("assistant"):
            with st.spinner("Zooming..."):

                prompt = f"""
Zoom into: {user_input}

Crop tightly and enhance details.
Do not change anything else.
"""

                image = edit_image(prompt, st.session_state.last_image)

                if image:
                    st.image(image)
                    st.session_state.last_image = image

                    st.session_state.chat_memory.append({
                        "user": user_input,
                        "bot": "Zoomed view",
                        "image": image
                    })
                else:
                    st.write("⚠️ Zoom failed")

    # ============================
    # CHAT
    # ============================
    else:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                response = chat_with_ai(user_input)

                st.write(response)

                st.session_state.chat_memory.append({
                    "user": user_input,
                    "bot": response
                })

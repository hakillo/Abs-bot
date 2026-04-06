# import streamlit as st
# import requests
# import time

# API_URL = "http://127.0.0.1:8000/chat"

# st.title("🧠 Census Bureau's Chatbot")

# # Session state
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # 🌐 Toggle
# use_web = st.toggle("🌐 Allow web access if needed", value=False)

# # Display chat
# for role, msg in st.session_state.messages:
#     with st.chat_message("user" if role == "You" else "assistant"):
#         st.markdown(msg)

# # Input (Enter to send)
# user_input = st.chat_input("Ask ABS...AI is experimental.")

# if user_input:
#     # Show user message
#     st.session_state.messages.append(("You", user_input))
#     with st.chat_message("user"):
#         st.markdown(user_input)

#     # Call backend
#     try:
#         response = requests.post(
#             API_URL,
#             json={
#                 "question": user_input,
#                 "allow_web": use_web
#             },
#             timeout=60
#         )
#         response.raise_for_status()
#         answer = response.json().get("answer", "No answer received!")
#     except requests.exceptions.RequestException as e:
#         answer = f"Error: {e}"

#     # Streaming effect
#     with st.chat_message("assistant"):
#         placeholder = st.empty()
#         text = ""
#         for char in answer:
#             text += char
#             placeholder.markdown(text)
#             time.sleep(0.01)

#     st.session_state.messages.append(("Bot", answer))
import streamlit as st
import requests
import time

API_URL_CHAT = "http://127.0.0.1:8000/chat"
API_URL_UPLOAD = "http://127.0.0.1:8000/upload"  # New endpoint for document ingestion

st.title("🧠 Census Bureau's Chatbot")

# # -------- Upload document --------
# uploaded_file = st.file_uploader("📄 Upload your ABS DOCX document", type=["docx"])
# if uploaded_file:
#     files = {"file": (uploaded_file.name, uploaded_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
#     try:
#         response = requests.post(API_URL_UPLOAD, files=files, timeout=60)
#         response.raise_for_status()
#         st.success("✅ Document uploaded and processed successfully!")
#     except requests.exceptions.RequestException as e:
#         st.error(f"Error uploading document: {e}")

# -------- Session state for chat --------
if "messages" not in st.session_state:
    st.session_state.messages = []

# 🌐 Toggle for web access
use_web = st.toggle("🌐 Allow web access if needed", value=False)

# Display chat messages
for role, msg in st.session_state.messages:
    with st.chat_message("user" if role == "You" else "assistant"):
        st.markdown(msg)

# Input box
user_input = st.chat_input("Ask ABS...      AI is experimental!")

if user_input:
    st.session_state.messages.append(("You", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call backend for chat
    try:
        response = requests.post(
            API_URL_CHAT,
            json={
                "question": user_input,
                "allow_web": use_web
            },
            timeout=60
        )
        response.raise_for_status()
        answer = response.json().get("answer", "No answer received!")
    except requests.exceptions.RequestException as e:
        answer = f"Error: {e}"

    # Streaming effect
    with st.chat_message("assistant"):
        placeholder = st.empty()
        text = ""
        for char in answer:
            text += char
            placeholder.markdown(text)
            time.sleep(0.01)

    st.session_state.messages.append(("Bot", answer))
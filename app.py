# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_chroma import Chroma
# from duckduckgo_search import DDGS
# import ollama

# # -------- Memory --------
# class Memory:
#     def __init__(self):
#         self.chat_history = []

#     def get_context(self):
#         return "\n".join([f"User: {q}\nAssistant: {a}" for q, a in self.chat_history])

#     def add(self, question, answer):
#         self.chat_history.append((question, answer))

# memory = Memory()

# # -------- App --------
# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # -------- Embeddings + DB --------
# embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# db = Chroma(persist_directory="db", embedding_function=embeddings)

# # -------- Request Model --------
# class Query(BaseModel):
#     question: str
#     allow_web: bool = False

# # -------- RAG Retrieval --------
# def retrieve(query):
#     docs = db.similarity_search(query, k=7)

#     if not docs:
#         return "", True

#     context = "\n".join([d.page_content for d in docs])

#     # simple weakness check
#     is_weak = len(context.strip()) < 100

#     return context, is_weak

# # -------- Web Search --------
# def search_web(query):
#     results = []
#     with DDGS() as ddgs:
#         for r in ddgs.text(query, max_results=5):
#             results.append(f"""
# Title: {r.get('title', '')}
# Snippet: {r.get('body', '')}
# """)
#     return "\n".join(results)

# def generate(question, context, history):
#     prompt = f"""
# You are a helpful AI assistant.

# IMPORTANT RULES:
# - You DO NOT have direct internet access.
# - You ONLY know what is provided in the context below.
# - If the answer is not in the context, say "I don't know based on the available information."
# - If Web Context is present, it may contain recent or external information.

# Chat History:
# {history}

# --- CONTEXT START ---
# {context}
# --- CONTEXT END ---

# User Question:
# {question}
# """

#     response = ollama.chat(
#         model="mistral",
#         messages=[{"role": "user", "content": prompt}]
#     )

#     return response.get("message", {}).get("content", "No response.")

# # -------- Endpoint --------
# @app.post("/chat")
# async def chat(q: Query):
#     if not q.question.strip():
#         return {"answer": "Please ask a question."}

#     # Retrieve RAG context
#     rag_context, is_weak = retrieve(q.question)

#     # Controlled web access
#     web_context = ""
#     used_web = False
#     if is_weak and q.allow_web:
#         web_context = search_web(q.question)
#         used_web = True

#     # Combine contexts for the LLM
#     combined_context = f"""
# Local Context:
# {rag_context}

# Web Context:
# {web_context}
# """

#     # Get chat history
#     history = memory.get_context()

#     # Generate answer
#     answer = generate(q.question, combined_context, history)

#     # Save to memory
#     memory.add(q.question, answer)

#     # Return answer + web usage flag
#     return {
#         "answer": answer,
#         "used_web": used_web
#     }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import ollama

# -------- Memory --------
class Memory:
    def __init__(self):
        self.chat_history = []

    def get_context(self):
        return "\n".join([f"User: {q}\nAssistant: {a}" for q, a in self.chat_history])

    def add(self, question, answer):
        self.chat_history.append((question, answer))

memory = Memory()

# -------- App --------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Embeddings + DB (load once) --------
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="db", embedding_function=embeddings)

# -------- Request Model --------
class Query(BaseModel):
    question: str
    allow_web: bool = False

# -------- RAG Retrieval (optimized) --------
def retrieve(query):
    # Increase k to cover more context
    docs = db.similarity_search(query, k=5)  # get top 8 chunks

    if not docs:
        return "", True

    # Include section headers in the context
    context = "\n\n".join([
        f"--- Section: {d.metadata.get('section', 'unknown')} ---\n{d.page_content}"
        for d in docs
    ])

    is_weak = len(context.strip()) < 150  # context too short
    return context, is_weak

# -------- Web Search --------
from duckduckgo_search import DDGS

def search_web(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(f"Title: {r.get('title','')}\nSnippet: {r.get('body','')}")
    return "\n".join(results)

# -------- Generate answer with LLM --------
def generate(question, context, history):
    prompt = f"""
You are a helpful AI assistant for the Annual Business Survey (ABS).

IMPORTANT RULES:
- You DO NOT have direct internet access unless Web Context is provided.
- Answer ONLY based on the context below.
- If the answer is not in the context, say "I don't know based on the available information."

Chat History:
{history}

--- CONTEXT START ---
{context}
--- CONTEXT END ---

User Question:
{question}
"""
    response = ollama.chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.get("message", {}).get("content", "No response.")

# -------- Chat endpoint --------
@app.post("/chat")
async def chat(q: Query):
    if not q.question.strip():
        return {"answer": "Please ask a question."}

    # RAG retrieval
    rag_context, is_weak = retrieve(q.question)

    # Optional web context if RAG is weak and allowed
    web_context = ""
    used_web = False
    if is_weak and q.allow_web:
        web_context = search_web(q.question)
        used_web = True

    combined_context = f"Local Context:\n{rag_context}\n\nWeb Context:\n{web_context}"

    # Chat history
    history = memory.get_context()

    # Generate answer
    answer = generate(q.question, combined_context, history)

    # Save in memory
    memory.add(q.question, answer)

    return {"answer": answer, "used_web": used_web}
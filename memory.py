# class ChatMemory:
#     def __init__(self):
#         self.history = []

#     def add(self, user, bot):
#         self.history.append((user, bot))

#     def get_context(self, last_n=3):
#         context = ""
#         for u, b in self.history[-last_n:]:
#             context += f"User: {u}\nAssistant: {b}\n"
#         return context

# memory = ChatMemory()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from duckduckgo_search import DDGS
import ollama

# -------- Chat Memory --------
class ChatMemory:
    def __init__(self):
        self.history = []

    def add(self, user, bot):
        self.history.append((user, bot))

    def get_context(self, last_n=3):
        context = ""
        for u, b in self.history[-last_n:]:
            context += f"User: {u}\nAssistant: {b}\n"
        return context

memory = ChatMemory()

# -------- FastAPI App --------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Embeddings + Chroma DB --------
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="db", embedding_function=embeddings)

# -------- Request Model --------
class Query(BaseModel):
    question: str
    allow_web: bool = False

# -------- RAG Retrieval --------
def retrieve(query):
    # Retrieve top 8 chunks for better coverage
    docs = db.similarity_search(query, k=8)
    if not docs:
        return "", True

    context = "\n\n".join([
        f"--- Section: {d.metadata.get('section', 'unknown')} ---\n{d.page_content}"
        for d in docs
    ])

    is_weak = len(context.strip()) < 150
    return context, is_weak

# -------- Web Search --------
def search_web(query):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(f"Title: {r.get('title','')}\nSnippet: {r.get('body','')}")
    return "\n".join(results)

# -------- Generate Answer --------
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

# -------- Chat Endpoint --------
@app.post("/chat")
async def chat(q: Query):
    if not q.question.strip():
        return {"answer": "Please ask a question."}

    # Retrieve relevant local context
    rag_context, is_weak = retrieve(q.question)

    # Optional web context if RAG is weak and user allows it
    web_context = ""
    used_web = False
    if is_weak and q.allow_web:
        web_context = search_web(q.question)
        used_web = True

    # Combine contexts
    combined_context = f"Local Context:\n{rag_context}\n\nWeb Context:\n{web_context}"

    # Include last 3 messages from memory
    history = memory.get_context(last_n=3)

    # Generate answer from LLM
    answer = generate(q.question, combined_context, history)

    # Save chat history
    memory.add(q.question, answer)

    return {"answer": answer, "used_web": used_web}
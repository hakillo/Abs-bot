
# from langchain_community.document_loaders import Docx2txtLoader
# #from langchain.text_splitter import CharacterTextSplitter
# from langchain_text_splitters import CharacterTextSplitter
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.vectorstores import Chroma

# # Load DOCX
# loader = Docx2txtLoader("data/abs.docx")
# documents = loader.load()
# print(f"Loaded {len(documents)} documents.")

# # Split text
# splitter = CharacterTextSplitter(chunk_size=700, chunk_overlap=80)
# docs = splitter.split_documents(documents)
# print(f"Split into {len(docs)} chunks.")

# # Embeddings
# embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# # Store in Chroma vector DB
# db = Chroma.from_documents(docs, embeddings, persist_directory="db")

# print("✅ Ingested")

import os
import re
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ---------------------------
# 1. Load DOCX
# ---------------------------
doc_path = "data/absr.docx"
if not os.path.exists(doc_path):
    raise FileNotFoundError(f"Document not found: {doc_path}")

loader = Docx2txtLoader(doc_path)
raw_docs = loader.load()
print(f"✅ Loaded {len(raw_docs)} document(s)")

full_text = "\n".join([d.page_content for d in raw_docs])

# ---------------------------
# 2. Section-aware splitting
# ---------------------------
SECTION_HEADERS = [
    "Important Update",
    "Purpose",
    "Coverage",
    "Content",
    "Frequency",
    "Methods",
    "Data Products",
    "Uses",
    "Key FAQs",
    "Contact"
]

def split_by_sections(text):
    pattern = r"(" + "|".join(SECTION_HEADERS) + r")"
    parts = re.split(pattern, text)

    sections = []
    current_header = None

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if part in SECTION_HEADERS:
            current_header = part
        else:
            sections.append({
                "header": current_header or "General",
                "content": part
            })

    return sections

sections = split_by_sections(full_text)
print(f"✅ Identified {len(sections)} sections")

# ---------------------------
# 3. Extract FAQs separately
# ---------------------------
def extract_faqs(section_text):
    faqs = []
    qa_pairs = re.split(r"\n(?=[A-Z][^\n]+\?)", section_text)
    for pair in qa_pairs:
        if "?" in pair:
            parts = pair.split("?", 1)
            question = parts[0].strip() + "?"
            answer = parts[1].strip()
            if answer:
                faqs.append((question, answer))
    return faqs

# ---------------------------
# 4. Chunking with metadata
# ---------------------------
splitter = RecursiveCharacterTextSplitter(
    chunk_size=700,
    chunk_overlap=120,
    separators=["\n\n", "\n", ".", " ", ""]
)

texts = []
metadatas = []

for sec in sections:
    header = sec["header"]
    content = sec["content"]

    if header == "Key FAQs":
        faq_pairs = extract_faqs(content)
        for q, a in faq_pairs:
            texts.append(f"Q: {q}\nA: {a}")
            metadatas.append({
                "section": "FAQ",
                "type": "qa",
                "question": q
            })
    else:
        chunks = splitter.split_text(content)
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({
                "section": header,
                "type": "content"
            })

print(f"✅ Created {len(texts)} structured chunks")

# ---------------------------
# 5. Embeddings
# ---------------------------
model_name = "all-MiniLM-L6-v2"
embeddings = HuggingFaceEmbeddings(model_name=model_name)
print(f"✅ Using embeddings model: {model_name}")

# ---------------------------
# 6. Store in Chroma
# ---------------------------
persist_dir = "db"

db = Chroma.from_texts(
    texts=texts,
    embedding=embeddings,
    metadatas=metadatas,
    persist_directory=persist_dir
)

print(f"✅ Stored {len(texts)} chunks in Chroma")
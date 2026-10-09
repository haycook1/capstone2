# agents/qualitative.py
import chromadb
from openai import OpenAI
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
model = SentenceTransformer("all-MiniLM-L6-v2")

# Qualitative agent function for retrieving and answering questions based on enterprise documentation.

def retrieve(query: str, top_k: int = 5) -> list[dict]:
    chroma = chromadb.PersistentClient(path="./data/chroma")
    collection = chroma.get_collection("enterprise-docs")
    embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=top_k)
    return [
        {
            "content": doc,
            "source": meta["source"],
            "chunk": meta["chunk"]
        }
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

# Function to build the prompt for the gemini model based on retrieved chunks.

def build_prompt(query: str, chunks: list[dict]) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"[Source {i+1}: {chunk['source']}]\n{chunk['content']}\n\n"

    return f"""You are a helpful enterprise documentation assistant.
Answer the question using ONLY the context provided below.
If the answer is not in the context, say "I cannot find this information in the provided documents."
Always cite the source number(s) you used.

CONTEXT:
{context}

QUESTION: {query}

ANSWER:"""

# Main runner function for the qualitative agent.

def run(query: str) -> dict:
    chunks = retrieve(query)
    prompt = build_prompt(query, chunks)
    message = client.chat.completions.create(
        model="gemini-3.5-flash-lite",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return {
        "answer": message.choices[0].message.content.strip(),
        "chunks": chunks,
        "input_tokens": message.usage.prompt_tokens,
        "output_tokens": message.usage.completion_tokens
    }
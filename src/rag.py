import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GEN_MODEL = "gpt-4.1-mini"
EMBED_MODEL = "text-embedding-3-small"

def get_embedding(text: str):
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding

def load_chunks(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    return chunks

def retrieve_top_chunk(question: str, chunks: list[str]) -> str:
    question_emb = np.array(get_embedding(question)).reshape(1, -1)
    chunk_embs = np.array([get_embedding(chunk) for chunk in chunks])
    sims = cosine_similarity(question_emb, chunk_embs)[0]
    best_idx = int(np.argmax(sims))
    return chunks[best_idx]

def ask_with_rag(question: str, context: str) -> str:
    prompt = f"""
Use only the context below to answer the question.
If the answer is not in the context, say: "Not found in provided context."

Context:
{context}

Question:
{question}
"""
    response = client.responses.create(
        model=GEN_MODEL,
        input=prompt
    )
    return response.output_text.strip()

def main():
    df = pd.read_csv("data/questions.csv")
    chunks = load_chunks("data/documents.txt")

    contexts = []
    rag_answers = []

    for question in df["question"]:
        print(f"Processing: {question}")
        context = retrieve_top_chunk(question, chunks)
        answer = ask_with_rag(question, context)
        print(f"Context: {context}")
        print(f"Answer: {answer}\n")
        contexts.append(context)
        rag_answers.append(answer)

    df["retrieved_context"] = contexts
    df["rag_answer"] = rag_answers
    df.to_csv("outputs/rag_results.csv", index=False)

    print("\nDone! Results saved in outputs/rag_results.csv")

if __name__ == "__main__":
    main()
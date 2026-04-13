# LLM Hallucination Analysis using RAG

## 📌 Overview
This project analyzes hallucination behavior in Large Language Models (LLMs) by comparing:

- Baseline LLM (direct answering)
- Retrieval-Augmented Generation (RAG)

The goal is to evaluate how RAG improves reliability by reducing hallucinations on out-of-context queries.

---

## 🧠 Problem Statement
LLMs often generate incorrect or fabricated answers (hallucinations), especially when asked about:

- Fictional entities
- Unknown facts
- Out-of-context questions

---

## ⚙️ Methodology

### 1. Baseline Model
- Directly queries the LLM
- No external context
- Prone to hallucination

### 2. RAG Model
- Retrieves relevant context from a document
- Uses embeddings + similarity search
- If no relevant context → abstains

---

## 📂 Project Structure
llm_hallucination_project/
│
├── data/
│ ├── questions.csv
│ └── documents.txt
│
├── src/
│ ├── baseline.py
│ ├── rag.py
│ └── evaluate.py
│
├── outputs/
│ ├── baseline_results.csv
│ ├── rag_results.csv
│ └── final_results.csv
│
└── README.md
---

## 🚀 Results
- Baseline: Produces hallucinations on unknown queries
- RAG: Reduces hallucination by abstaining when context is missing

---

## 🔮 Future Work
- Expand dataset (100+ questions)
- Add evaluation metrics (accuracy, hallucination rate)
- Improve retrieval (top-k, thresholding)

---

## 📎 Author
Chaitanya Jajula
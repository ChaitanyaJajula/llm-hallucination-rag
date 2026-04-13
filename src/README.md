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

This project demonstrates how RAG helps mitigate this issue.

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

## 🧪 Experiment Setup

Dataset includes:
- Factual questions
- Fictional questions (e.g., Wakanda, Mars)
- Out-of-context queries

---

## 📊 Results

| Model     | Correct | Hallucinated | Abstained |
|----------|--------|--------------|-----------|
| Baseline | 5      | 3            | 0         |
| RAG      | 5      | 0            | 3         |

### 🔍 Key Insight
- Baseline model **hallucinates** on unknown queries  
- RAG model **avoids hallucination** by abstaining  

---

## 🚀 Future Work

- Expand dataset to 100+ questions
- Add evaluation metrics (accuracy, hallucination rate)
- Improve retrieval (top-k chunks, similarity threshold)
- Scale to larger datasets

---

## 🛠️ Technologies Used

- Python
- OpenAI API
- Pandas
- NumPy
- Scikit-learn

---

## 📎 How to Run

```bash
# Activate environment
venv\Scripts\activate

# Run baseline
python src\baseline.py

# Run RAG
python src\rag.py

# Run evaluation
python src\evaluate.py


## 👨‍💻 Author

Chaitanya Jajula

## 🔍 Key Insight

- Baseline LLM tends to hallucinate on unknown queries  
- RAG reduces hallucination by grounding responses in context  
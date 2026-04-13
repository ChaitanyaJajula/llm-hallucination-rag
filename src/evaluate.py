import pandas as pd

def label_answer(answer: str, ground_truth: str) -> str:
    answer_lower = str(answer).strip().lower()
    truth_lower = str(ground_truth).strip().lower()

    if truth_lower in answer_lower:
        return "correct"
    elif "not found in provided context" in answer_lower:
        return "abstained"
    else:
        return "hallucinated_or_incorrect"

def main():
    base_df = pd.read_csv("outputs/baseline_results.csv")
    rag_df = pd.read_csv("outputs/rag_results.csv")

    df = base_df.merge(
        rag_df[["question", "retrieved_context", "rag_answer"]],
        on="question"
    )

    df["baseline_label"] = df.apply(
        lambda row: label_answer(row["baseline_answer"], row["ground_truth"]),
        axis=1
    )

    df["rag_label"] = df.apply(
        lambda row: label_answer(row["rag_answer"], row["ground_truth"]),
        axis=1
    )

    df.to_csv("outputs/final_results.csv", index=False)

    print("\nBaseline counts:")
    print(df["baseline_label"].value_counts())

    print("\nRAG counts:")
    print(df["rag_label"].value_counts())

    print("\nSaved to outputs/final_results.csv")

if __name__ == "__main__":
    main()
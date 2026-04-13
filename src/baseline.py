import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd

# Load API key from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Model name
MODEL = "gpt-4.1-mini"

# Function to ask LLM
def ask_llm(question: str) -> str:
    response = client.responses.create(
        model=MODEL,
        input=f"Answer this factual question briefly and directly:\n\n{question}"
    )
    return response.output_text.strip()

# Main function
def main():
    # Load questions
    df = pd.read_csv("data/questions.csv")

    answers = []

    # Loop through questions
    for q in df["question"]:
        print(f"Asking: {q}")
        ans = ask_llm(q)
        print(f"Answer: {ans}\n")
        answers.append(ans)

    # Save results
    df["baseline_answer"] = answers
    df.to_csv("outputs/baseline_results.csv", index=False)

    print("\n✅ Done! Results saved in outputs/baseline_results.csv")

# Run program
if __name__ == "__main__":
    main()
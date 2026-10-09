# main.py
from agents.manager import run


# Main entry point for the Spoonful Enterprise RAG System.
def main():
    print("Spoonful Enterprise RAG System")
    print("Type 'exit' to quit.\n")
    while True:
        query = input("Ask a question: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        if not query:
            continue
        run(query)

if __name__ == "__main__":
    main()

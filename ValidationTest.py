import agents.quantitative as quantitative
import sqlite3



def fake_retrieve(query: str, top_k: int = 5) -> list[dict]:
    return [
        {
            "content": (
                "The company cafeteria serves breakfast from 7:00 to 9:00 a.m."
            ),
            "source": "irrelevant.txt",
            "chunk": 0,
        },
        {
            "content": (
                "Employees should submit printer requests through the "
                "facilities portal."
            ),
            "source": "irrelevant.txt",
            "chunk": 1,
        },
    ]


# Replace quantitative.py's normal Chroma retrieval for this test.
quantitative.retrieve = fake_retrieve

question = "What was the company's Q4 revenue growth percentage?"

result = quantitative.run(question)
answer = result["answer"]

print("Model answer:")
print(answer)

if "cannot find" in answer.lower():
    print("\nValidation: PASSED")
else:
    print("\nValidation: FAILED")
    raise AssertionError(
        "The quantitative role answered using irrelevant context."
    )


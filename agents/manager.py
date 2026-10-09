from openai import OpenAI
import os
from dotenv import load_dotenv
from agents import qualitative, quantitative
from validation.validator import validate_qualitative, validate_quantitative
from tokenomics.logger import log

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)



def validation_passed(validation: dict | str) -> bool:
    if isinstance(validation, dict):
        if "flag" in validation:
            return validation["flag"] is False

        if "valid" in validation:
            return validation["valid"] is True

    if isinstance(validation, str):
        return validation.strip().upper() in {
            "PASSED",
            "VALID",
            "OK",
        }

    return False



def safe_answer(label: str, answer: str, validation: dict) -> str:
    """Return model output only when validation passes."""
    if validation_passed(validation) and str(answer).strip():
        return str(answer).strip()

    warning = validation.get(
        "warning",
        validation.get("reason", "The response failed validation.")
    )

    return f"{label} response withheld: {warning}"


def classify(query: str) -> str:
    message = client.chat.completions.create(
        model="gemini-3.5-flash-lite",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": f"""Classify this query as exactly one of: qualitative, quantitative, both.

qualitative = questions about policies, processes, procedures, explanations, documentation

quantitative = questions about numbers, metrics, trends, comparisons, SQL-queryable data

both = questions that need both document search and data analysis

Query: {query}

Reply with one word only: qualitative, quantitative, or both."""
        }]
    )

    route = message.choices[0].message.content.strip().lower()

    log(
        query,
        "manager-classifier",
        message.usage.prompt_tokens,
        message.usage.completion_tokens
    )

    return route if route in ["qualitative", "quantitative", "both"] else "qualitative"


def run(query: str):
    print(f"\nQuery: {query}")

    route = classify(query)
    print(f"Route: {route}")

    qual_result = None
    quant_result = None

    if route in ["qualitative", "both"]:
        qual_result = qualitative.run(query)

        qual_validation = validate_qualitative(
            qual_result["answer"],
            qual_result["chunks"]
        )

        log(
            query,
            "qualitative",
            qual_result["input_tokens"],
            qual_result["output_tokens"]
        )

        qual_answer = safe_answer(
            "Qualitative",
            qual_result["answer"],
            qual_validation
        )

        if not validation_passed(qual_validation):
            print(
                f"\n⚠️ VALIDATION WARNING: "
                f"{qual_validation.get('warning', 'Response failed validation.')}"
            )

        print(f"\n[Qualitative]\n{qual_answer}")

    if route in ["quantitative", "both"]:
        quant_result = quantitative.run(query)

        sql = quant_result.get("sql", "")
        sql_validation = quant_result.get(
            "validation",
            {
                "valid": False,
                "reason": "No SQL validation result was returned."
            }
        )

        if sql_validation.get("valid") is True:
            answer_validation = validate_quantitative(
                quant_result["answer"],
                sql,
                sql_validation
            )
        else:
            answer_validation = {
                "flag": True,
                "warning": (
                    "SQL was rejected before the quantitative answer "
                    f"could be displayed: {sql_validation.get('reason', 'Unknown reason')}"
                )
            }

        log(
            query,
            "quantitative",
            quant_result["input_tokens"],
            quant_result["output_tokens"]
        )

        quant_answer = safe_answer(
            "Quantitative",
            quant_result.get("answer", ""),
            answer_validation
        )

        if not validation_passed(answer_validation):
            print(
                f"\n⚠️ VALIDATION WARNING: "
                f"{answer_validation.get('warning', 'Response failed validation.')}"
            )

        print(f"\n[Quantitative]\n{quant_answer}")

        if (
            sql_validation.get("valid") is True
            and validation_passed(answer_validation)
        ):
            print(f"SQL used: {sql}")

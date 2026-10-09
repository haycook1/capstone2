# validation/validator.py

# Validation functions for qualitative and quantitative responses.
def validate_qualitative(answer: str, chunks: list[dict]) -> dict:
    sources_cited = []
    for i, chunk in enumerate(chunks):
        if f"Source {i+1}" in answer:
            sources_cited.append(chunk["source"])

    grounded = len(sources_cited) > 0
    refused = "cannot find" in answer.lower()

    return {
        "is_grounded": grounded,
        "refused_to_answer": refused,
        "sources_cited": sources_cited,
        "flag": not grounded and not refused,
        "warning": "Response may not be grounded in source documents" if (not grounded and not refused) else None
    }


# Helper function to check if SQL validation has passed.
def _sql_validation_passed(sql_validation: dict | str) -> bool:
    if isinstance(sql_validation, dict):
        return sql_validation.get("valid") is True

    if isinstance(sql_validation, str):
        return sql_validation.strip().upper() in {
            "PASSED",
            "VALID",
            "OK",
        }

    return False

# Main validation function for quantitative responses.
def validate_quantitative(
    answer: str,
    sql: str,
    sql_validation: dict | str,
) -> dict:
    if not _sql_validation_passed(sql_validation):
        return {
            "flag": True,
            "warning": f"SQL validation failed: {sql_validation}",
        }

    if not sql.strip().upper().startswith("SELECT"):
        return {
            "flag": True,
            "warning": "The quantitative response did not use a SELECT query.",
        }

    if not str(answer).strip():
        return {
            "flag": True,
            "warning": "The quantitative agent returned an empty answer.",
        }

    return {
        "flag": False,
        "warning": "Quantitative response passed validation.",
    }

import os
import re
import sqlite3

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_PATH = "data/enterprise.db"

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

SCHEMA_CONTEXT = """
Available SQLite tables:

- sales(id, region, product, revenue, date, units_sold)
- customers(id, name, industry, churn_date, satisfaction_score)
- employees(id, department, satisfaction_score, tenure_years)

Metric rules:
- Average revenue per unit means SUM(revenue) * 1.0 / NULLIF(SUM(units_sold), 0).
- Do not use AVG(revenue) for average revenue per unit.
- AVG(revenue) means average revenue per sale and should be used only when explicitly requested.
- If a year is requested, apply the appropriate date filter.
- Return exactly one read-only SELECT statement.
"""


def usage_tokens(usage, field: str) -> int:
    return int(getattr(usage, field, 0) or 0)


def validate_sql(query: str) -> dict:
    cleaned = query.strip()

    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        return {
            "valid": False,
            "reason": "Only SELECT queries are permitted.",
        }

    blocked = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "ATTACH",
        "PRAGMA",
    ]

    for word in blocked:
        if re.search(rf"\b{word}\b", cleaned.upper()):
            return {
                "valid": False,
                "reason": f"Blocked keyword: {word}",
            }

    if ";" in cleaned.rstrip(";"):
        return {
            "valid": False,
            "reason": "Multiple SQL statements are not permitted.",
        }

    return {
        "valid": True,
        "reason": "OK",
    }


def generate_sql(query: str) -> dict:
    message = client.chat.completions.create(
        model="gemini-3.5-flash-lite",
        max_tokens=256,
        messages=[
            {
                "role": "system",
                "content": SCHEMA_CONTEXT,
            },
            {
                "role": "user",
                "content": query,
            },
        ],
    )

    sql = message.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return {
        "sql": sql,
        "input_tokens": usage_tokens(
            message.usage,
            "prompt_tokens",
        ),
        "output_tokens": usage_tokens(
            message.usage,
            "completion_tokens",
        ),
    }

def normalize_metric_sql(question: str, sql: str) -> tuple[str, list[str]]:
    """
    Corrects the known AVG(revenue) mistake when the user asks
    for average revenue per unit.
    """
    changes = []

    asks_for_revenue_per_unit = re.search(
        r"average\s+revenue\s+per\s+unit|revenue\s+per\s+unit",
        question,
        flags=re.IGNORECASE,
    )

    uses_average_revenue = re.search(
        r"\bAVG\s*{{{{\(\s*revenue\s*\)}}}}",
        sql,
        flags=re.IGNORECASE,
    )

    if asks_for_revenue_per_unit and uses_average_revenue:
        sql = re.sub(
            r"\bAVG\s*{{{{\(\s*revenue\s*\)}}}}",
            "SUM(revenue) * 1.0 / NULLIF(SUM(units_sold), 0)",
            sql,
            flags=re.IGNORECASE,
        )

        sql = re.sub(
            r"\baverage_revenue_per_sale\b",
            "average_revenue_per_unit",
            sql,
            flags=re.IGNORECASE,
        )

        changes.append(
            "Replaced AVG(revenue) with "
            "SUM(revenue) / SUM(units_sold) to calculate "
            "average revenue per unit."
        )

    return sql, changes


def interpret_results(
    query: str,
    sql: str,
    rows: list[dict],
) -> dict:
    message = client.chat.completions.create(
        model="gemini-3.5-flash-lite",
        max_tokens=512,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer only from the supplied SQLite results. "
                    "Do not invent values. Clearly state when no rows "
                    "were returned."
                    "Treat average_revenue_per_unit as total revenue divided by total units sold. "
                    "Do not describe it as average revenue per sale."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question: {query}\n"
                    f"SQL used: {sql}\n"
                    f"SQLite results: {rows}\n\n"
                    "Provide a concise business interpretation."
                ),
            },
        ],
    )

    return {
        "answer": message.choices[0].message.content.strip(),
        "input_tokens": usage_tokens(
            message.usage,
            "prompt_tokens",
        ),
        "output_tokens": usage_tokens(
            message.usage,
            "completion_tokens",
        ),
    }


def run(query: str) -> dict:
    generated = generate_sql(query)
    sql = generated["sql"]
    sql, sql_adjustments = normalize_metric_sql(query, sql)

    if sql_adjustments:
        print("\n[SQL NORMALIZATION]")
        for adjustment in sql_adjustments:
            print(f"- {adjustment}")

    sql_validation = validate_sql(sql)
    
    if not sql_validation["valid"]:
        return {
            "answer": f"Query blocked: {sql_validation['reason']}",
            "sql": sql,
            "sql_adjustments": sql_adjustments,
            "rows": [],
            "validation": sql_validation,
            "input_tokens": generated["input_tokens"],
            "output_tokens": generated["output_tokens"],
        }

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(sql).fetchall()
            data = [dict(row) for row in rows]

    except sqlite3.Error as error:
        return {
            "answer": f"Query execution failed: {error}",
            "sql": sql,
            "rows": [],
            "validation": {
                "valid": False,
                "reason": str(error),
            },
            "input_tokens": generated["input_tokens"],
            "output_tokens": generated["output_tokens"],
        }

    interpretation = interpret_results(query, sql, data)

    total_input_tokens = (
        generated["input_tokens"]
        + interpretation["input_tokens"]
    )
    total_output_tokens = (
        generated["output_tokens"]
        + interpretation["output_tokens"]
    )

    return {
        "answer": interpretation["answer"],
        "sql": sql,
        "sql_adjustments": sql_adjustments,
        "rows": data,
        "validation": sql_validation,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
    }

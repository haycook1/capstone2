import json
import os
from datetime import datetime, timezone

# Tokenomics logger for tracking API usage and costs.
COST_PER_1K_INPUT = float(os.getenv("COST_PER_1K_INPUT", "0.003"))
COST_PER_1K_OUTPUT = float(os.getenv("COST_PER_1K_OUTPUT", "0.015"))
LOG_PATH = os.getenv("TOKENOMICS_LOG_PATH", "tokenomics_log.jsonl")

# Function to log individual agent calls with token usage and cost.
def log(
    query: str,
    agent: str,
    input_tokens: int,
    output_tokens: int,
    record_type: str = "agent_call",
) -> dict:
    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)

    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT
    total_cost = input_cost + output_cost

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "record_type": record_type,
        "query": query,
        "agent": agent,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "cost_usd": round(total_cost, 6),
        "cost_per_1000_queries": round(total_cost * 1000, 2),
    }

    print(
        f"\n[TOKENOMICS] Agent: {agent} | "
        f"Input: {input_tokens} | Output: {output_tokens} | "
        f"Cost: ${total_cost:.6f}"
    )

    parent_directory = os.path.dirname(LOG_PATH)
    if parent_directory:
        os.makedirs(parent_directory, exist_ok=True)

    with open(LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")

    return entry

# Function to log the total usage for a query, including route and outcome.
def log_query_total(
    query: str,
    route: str,
    input_tokens: int,
    output_tokens: int,
    outcome: str,
) -> dict:
    return log(
        query=query,
        agent=f"query-total/{route}/{outcome}",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        record_type="query_total",
    )

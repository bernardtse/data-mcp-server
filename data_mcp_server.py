"""
Simple Python Data Analytics MCP Tool Server
- Loads CSV, row-based JSON, or row-based YAML datasets.
- Performs simple Python analysis: basic info, numeric summary, categorical summary.
- Output in plain text, readable by humans, and suitable for LLM interpretation.
- LLM is invited to provide a short summary of insights.
"""

import os
import json
import yaml
import pandas as pd
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

mcp = FastMCP("data-mcp-server")


# Data Loading

def _load_df(path: str) -> pd.DataFrame:
    """Load a dataset into a pandas DataFrame (CSV, row-based JSON, or row-based YAML)."""
    if not path:
        raise FileNotFoundError("No file path provided. Please provide the full path to a dataset.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}\nPlease provide the full path to a dataset.")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        return pd.read_csv(path)

    if ext in (".json", ".ndjson"):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list) and all(isinstance(i, dict) for i in raw):
            return pd.DataFrame(raw)
        raise ValueError("JSON structure not recognised as tabular. It must be a list of dictionaries.")

    if ext in (".yaml", ".yml"):
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, list) and all(isinstance(i, dict) for i in raw):
            return pd.DataFrame(raw)
        raise ValueError("YAML structure not recognised as tabular. It must be a list of dictionaries.")

    raise ValueError("Unsupported file type. Supported: CSV, JSON, YAML.")


# Analysis Functions

def analyse_numeric(df: pd.DataFrame) -> str:
    """Return summary statistics for numeric columns."""
    numeric = df.select_dtypes(include='number')
    if numeric.empty:
        return "No numeric columns found."
    return numeric.describe().round(3).to_string()


def analyse_categorical(df: pd.DataFrame) -> str:
    """Return the top 3 most common values per categorical column."""
    categorical = df.select_dtypes(include='object')
    if categorical.empty:
        return "No categorical columns found."
    results = []
    for col in categorical.columns:
        top = df[col].value_counts().head(3)
        results.append(f"\nTop values in '{col}':\n{top.to_string()}")
    return "\n".join(results)


# MCP Tool: Perform Full Analysis

@mcp.tool()
def analyse_by_path(file_path: str) -> CallToolResult:
    """
    Load the dataset and perform a simple Python analysis.
    The LLM is invited to briefly summarise the findings in natural language.
    """
    try:
        df = _load_df(file_path)
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Warning: {e}")])

    # Python-side analysis
    sections = [
        ("Basic Information", f"Rows: {len(df)}, Columns: {len(df.columns)}\nColumns: {list(df.columns)}"),
        ("Numeric Summary", analyse_numeric(df)),
        ("Categorical Summary", analyse_categorical(df))
    ]

    # Combine results
    report_text = "\n\n".join([f"=== {title} ===\n{content}" for title, content in sections])

    # Plain note for LLM
    llm_note = (
        "You may now provide a short 4–6 sentence summary describing what this dataset shows and any key patterns or observations."
    )

    final_text = f"Python analysis for: {file_path}\n\n{report_text}\n\n---\n{llm_note}"

    return CallToolResult(content=[TextContent(type="text", text=final_text)])


# Run MCP server

if __name__ == "__main__":
    mcp.run(transport="stdio")
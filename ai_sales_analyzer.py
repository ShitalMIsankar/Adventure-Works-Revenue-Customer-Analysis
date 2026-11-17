#!/usr/bin/env python3
"""
AI-assisted Sales Analysis & Data Quality Checker
- Analyzes a CSV sales file with pandas.
- Flags common data-quality issues.
- Produces summary CSVs, a Markdown report, and an AI prompt pack.
- Does not call an AI API: use the generated prompt with your preferred AI assistant,
  then independently validate any suggested conclusions.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

REQUIRED_COLUMNS = [
    "order_id", "order_date", "region", "product", "category",
    "quantity", "unit_price", "unit_cost"
]

def load_data(path: r"C:\Users\Lenovo\OneDrive\My Resume Files\Adventure Works Project Excel File.xlsx") -> pd.DataFrame:
    df = pd.read_csv(r"C:\Users\Lenovo\OneDrive\My Resume Files\Adventure Works Project Excel File.xlsx")
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_cols) +
            "\nExpected columns: " + ", ".join(REQUIRED_COLUMNS)
        )
    return df

def analyze(df: pd.DataFrame):
    data = df.copy()
    # Normalize date and numeric columns; keep original row count for audit.
    data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
    for col in ["quantity", "unit_price", "unit_cost"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    # Data quality flags. Rows may have multiple flags.
    issues = []
    for idx, row in data.iterrows():
        flags = []
        if row[REQUIRED_COLUMNS].isna().any():
            flags.append("Missing required value or invalid number/date")
        if pd.notna(row["order_id"]) and data["order_id"].duplicated(keep=False).iloc[idx]:
            flags.append("Duplicate order_id")
        if pd.notna(row["quantity"]) and row["quantity"] <= 0:
            flags.append("Quantity must be greater than zero")
        if pd.notna(row["unit_price"]) and row["unit_price"] < 0:
            flags.append("Negative unit_price")
        if pd.notna(row["unit_cost"]) and row["unit_cost"] < 0:
            flags.append("Negative unit_cost")
        if pd.notna(row["unit_price"]) and pd.notna(row["unit_cost"]) and row["unit_cost"] > row["unit_price"]:
            flags.append("Unit cost exceeds unit price")
        if flags:
            issues.append({
                "source_row": idx + 2,  # header is row 1; data starts row 2
                "order_id": row.get("order_id"),
                "issue": "; ".join(flags)
            })
    issues_df = pd.DataFrame(issues, columns=["source_row", "order_id", "issue"])

    # Calculate metrics only for rows with valid numeric inputs and positive quantity/price.
    valid = data.dropna(subset=["order_id", "order_date", "region", "product", "category",
                                "quantity", "unit_price", "unit_cost"]).copy()
    valid = valid[(valid["quantity"] > 0) & (valid["unit_price"] >= 0) & (valid["unit_cost"] >= 0)]
    valid["revenue"] = valid["quantity"] * valid["unit_price"]
    valid["cost"] = valid["quantity"] * valid["unit_cost"]
    valid["profit"] = valid["revenue"] - valid["cost"]
    valid["profit_margin_pct"] = valid["profit"].div(valid["revenue"].where(valid["revenue"] != 0)).mul(100)

    # Exclude duplicate order IDs from headline totals so they do not inflate metrics.
    duplicate_mask = valid["order_id"].duplicated(keep="first")
    headline = valid.loc[~duplicate_mask].copy()

    region_summary = headline.groupby("region", dropna=False).agg(
        orders=("order_id", "nunique"),
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        units_sold=("quantity", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    product_summary = headline.groupby(["product", "category"], dropna=False).agg(
        orders=("order_id", "nunique"),
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        units_sold=("quantity", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    monthly_summary = headline.assign(month=headline["order_date"].dt.to_period("M").astype(str)).groupby("month").agg(
        orders=("order_id", "nunique"),
        revenue=("revenue", "sum"),
        profit=("profit", "sum")
    ).reset_index().sort_values("month")

    totals = {
        "source_rows": len(df),
        "rows_with_issues": len(issues_df),
        "duplicate_order_ids": int(data["order_id"].duplicated(keep=False).sum()),
        "valid_rows_used": len(headline),
        "total_revenue": float(headline["revenue"].sum()),
        "total_profit": float(headline["profit"].sum()),
        "overall_margin_pct": float(headline["profit"].sum() / headline["revenue"].sum() * 100)
            if headline["revenue"].sum() else 0.0,
    }
    return data, issues_df, region_summary, product_summary, monthly_summary, totals, headline

def money(value):
    return f"{value:,.2f}"

def write_outputs(input_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    original = load_data(input_path)
    data, issues, regions, products, monthly, totals, headline = analyze(original)

    issues.to_csv(out_dir / "data_quality_issues.csv", index=False)
    regions.to_csv(out_dir / "region_summary.csv", index=False)
    products.to_csv(out_dir / "product_summary.csv", index=False)
    monthly.to_csv(out_dir / "monthly_summary.csv", index=False)

    top_region = regions.iloc[0] if not regions.empty else None
    top_product = products.iloc[0] if not products.empty else None
    report_lines = [
        "# Sales Analysis & Data Quality Report",
        "",
        "## Data quality",
        f"- Source rows: **{totals['source_rows']}**",
        f"- Rows flagged with one or more issues: **{totals['rows_with_issues']}**",
        f"- Rows used in headline metrics after validation and duplicate handling: **{totals['valid_rows_used']}**",
        f"- Rows belonging to duplicate order IDs: **{totals['duplicate_order_ids']}**",
        "",
        "## Headline metrics",
        f"- Revenue: **{money(totals['total_revenue'])}**",
        f"- Profit: **{money(totals['total_profit'])}**",
        f"- Overall profit margin: **{totals['overall_margin_pct']:.2f}%**",
        "",
        "## Initial observations",
    ]
    if top_region is not None:
        report_lines.append(
            f"- Highest-revenue region in this dataset: **{top_region['region']}** "
            f"({money(top_region['revenue'])} revenue)."
        )
    if top_product is not None:
        report_lines.append(
            f"- Highest-revenue product in this dataset: **{top_product['product']}** "
            f"({money(top_product['revenue'])} revenue)."
        )
    report_lines += [
        "- These are descriptive results from the supplied file, not proof of causation.",
        "- Review `data_quality_issues.csv` before using results for business decisions.",
        "- Headline metrics exclude rows with invalid required fields, non-positive quantities, negative prices/costs,",
        "  and later occurrences of duplicate order IDs. Check whether this policy fits your business rules.",
        "",
        "## Files generated",
        "- `data_quality_issues.csv`",
        "- `region_summary.csv`",
        "- `product_summary.csv`",
        "- `monthly_summary.csv`",
        "- `ai_analysis_prompt.txt`",
        "",
        "## AI validation reminder",
        "AI-generated interpretations may be wrong. Verify any claim against these summary files and the source rows.",
    ]
    (out_dir / "analysis_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    prompt = f"""You are helping analyze a sales dataset. Use only the facts in the attached report and summary CSVs.
Do not invent causes or business context. Separate observations from hypotheses.
Suggest 3 follow-up questions and 3 practical next analyses.
Before making a claim, identify which output file and column supports it.
Mention limitations, especially excluded rows and duplicate order handling.

Run summary:
- Source rows: {totals['source_rows']}
- Rows flagged: {totals['rows_with_issues']}
- Rows used in headline metrics: {totals['valid_rows_used']}
- Revenue: {money(totals['total_revenue'])}
- Profit: {money(totals['total_profit'])}
- Overall profit margin: {totals['overall_margin_pct']:.2f}%

Return:
1. Three evidence-based observations
2. Two possible explanations clearly labeled as hypotheses
3. Three follow-up analyses
4. A validation checklist of every numeric claim
"""
    (out_dir / "ai_analysis_prompt.txt").write_text(prompt, encoding="utf-8")

    print("Analysis complete.")
    print(f"Input: {input_path}")
    print(f"Output folder: {out_dir.resolve()}")
    print(f"Rows: {totals['source_rows']} | Flagged rows: {totals['rows_with_issues']} | "
          f"Revenue: {money(totals['total_revenue'])} | Profit: {money(totals['total_profit'])}")

def main():
    parser = argparse.ArgumentParser(description="Analyze a sales CSV and flag data-quality issues.")
    parser.add_argument("input_csv", help="Path to input CSV")
    parser.add_argument("--out", default="analysis_output", help="Output directory (default: analysis_output)")
    args = parser.parse_args()
    write_outputs(Path(args.input_csv), Path(args.out))

if __name__ == "__main__":
    main()

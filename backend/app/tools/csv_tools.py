from typing import Annotated, Literal

from pydantic import Field

from app.services.ml.toolkit import load_csv, profile_dataframe
from app.tools.registry import tool
from app.utils.files import resolve_data_file, to_jsonable


@tool(description="Summarize an uploaded CSV file: shape, column types, missing values, stats, first rows.")
def analyze_csv(
    filename: Annotated[str, Field(description="Uploaded CSV file name")],
) -> dict:
    df = load_csv(resolve_data_file(filename))
    return profile_dataframe(df, preview_rows=5)


@tool(description="Group a CSV by one column and aggregate another (sum, mean, count, min, max).")
def aggregate_csv(
    filename: Annotated[str, Field(description="CSV file name")],
    group_by: Annotated[str, Field(description="Column to group by")],
    value_column: Annotated[str, Field(description="Numeric column to aggregate")],
    agg: Literal["sum", "mean", "count", "min", "max"] = "sum",
    top_n: int = 20,
) -> dict:
    df = load_csv(resolve_data_file(filename))
    for col in (group_by, value_column):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found. Columns: {list(df.columns)}")
    series = df.groupby(group_by)[value_column].agg(agg).sort_values(ascending=False).head(top_n)
    rows = [{group_by: k, f"{agg}_{value_column}": v} for k, v in series.items()]
    return to_jsonable({"rows": rows})

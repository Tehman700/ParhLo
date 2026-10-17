"""Reusable scikit-learn workflow: load -> profile -> preprocess -> train -> evaluate -> save -> predict.

Usable from notebooks/scripts too:
    from app.services.ml.toolkit import load_csv, train_model, predict
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
    mean_absolute_error, mean_squared_error, r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.utils.files import to_jsonable

Task = Literal["auto", "classification", "regression"]
Algorithm = Literal["random_forest", "gradient_boosting", "linear"]

ALGORITHMS = {
    "classification": {
        "random_forest": lambda: RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        "gradient_boosting": lambda: GradientBoostingClassifier(random_state=42),
        "linear": lambda: LogisticRegression(max_iter=2000),
    },
    "regression": {
        "random_forest": lambda: RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
        "gradient_boosting": lambda: GradientBoostingRegressor(random_state=42),
        "linear": lambda: LinearRegression(),
    },
}


# ---------- loading & exploration ----------

def load_csv(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path)


def profile_dataframe(df: pd.DataFrame, preview_rows: int = 10) -> dict:
    numeric = df.select_dtypes(include="number")
    return to_jsonable({
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "missing": {c: int(n) for c, n in df.isna().sum().items()},
        "unique": {c: int(df[c].nunique()) for c in df.columns},
        "numeric_summary": numeric.describe().round(4).to_dict() if not numeric.empty else {},
        "preview": df.head(preview_rows).to_dict(orient="records"),
    })


def infer_task(y: pd.Series) -> Literal["classification", "regression"]:
    if pd.api.types.is_bool_dtype(y) or not pd.api.types.is_numeric_dtype(y):
        return "classification"
    if pd.api.types.is_integer_dtype(y) and y.nunique() <= 20:
        return "classification"
    return "regression"


# ---------- preprocessing ----------

def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    num_cols = X.select_dtypes(include="number").columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), num_cols),
        ("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", max_categories=30)),
        ]), cat_cols),
    ])


def drop_id_like(X: pd.DataFrame) -> list[str]:
    """Columns that are unique per row (ids, names) and would only cause overfitting."""
    return [
        c for c in X.columns
        if not pd.api.types.is_numeric_dtype(X[c]) and X[c].nunique() > 0.9 * len(X)
    ]


# ---------- training ----------

def models_dir() -> Path:
    d = get_settings().processed_dir / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def train_model(
    df: pd.DataFrame,
    target: str,
    task: Task = "auto",
    algorithm: Algorithm = "random_forest",
    test_size: float = 0.2,
    model_name: str | None = None,
    drop_columns: list[str] | None = None,
) -> dict:
    if target not in df.columns:
        raise ValueError(f"Target '{target}' not in columns: {list(df.columns)}")
    start = time.perf_counter()
    df = df.dropna(subset=[target])
    y = df[target]
    X = df.drop(columns=[target, *(drop_columns or [])])
    dropped = drop_id_like(X)
    X = X.drop(columns=dropped)

    resolved_task = infer_task(y) if task == "auto" else task
    stratify = y if resolved_task == "classification" and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )
    pipeline = Pipeline([
        ("prep", build_preprocessor(X)),
        ("model", ALGORITHMS[resolved_task][algorithm]()),
    ])
    pipeline.fit(X_train, y_train)
    preds = pipeline.predict(X_test)
    metrics = evaluate(resolved_task, y_test, preds)

    name = _safe_name(model_name or f"{target}_{algorithm}")
    meta = {
        "name": name,
        "target": target,
        "task": resolved_task,
        "algorithm": algorithm,
        "features": X.columns.tolist(),
        "dropped_columns": dropped,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metrics": metrics,
        "feature_importance": feature_importance(pipeline),
        "classes": [str(c) for c in pipeline.classes_] if hasattr(pipeline, "classes_") else None,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_ms": round((time.perf_counter() - start) * 1000, 1),
    }
    joblib.dump(pipeline, models_dir() / f"{name}.joblib")
    (models_dir() / f"{name}.json").write_text(json.dumps(to_jsonable(meta), indent=2), encoding="utf-8")
    return to_jsonable(meta)


def evaluate(task: str, y_true, y_pred) -> dict:
    if task == "classification":
        labels = sorted(pd.unique(pd.concat([pd.Series(y_true), pd.Series(y_pred)])).tolist(), key=str)
        return {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "f1_macro": round(float(f1_score(y_true, y_pred, average="macro")), 4),
            "labels": [str(lbl) for lbl in labels],
            "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
            "report": classification_report(y_true, y_pred, output_dict=True, zero_division=0),
        }
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    return {
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(rmse, 4),
    }


def feature_importance(pipeline: Pipeline, top_n: int = 15) -> list[dict]:
    model = pipeline.named_steps["model"]
    try:
        names = pipeline.named_steps["prep"].get_feature_names_out()
    except Exception:
        return []
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
    elif hasattr(model, "coef_"):
        coef = np.abs(model.coef_)
        values = coef.mean(axis=0) if coef.ndim > 1 else coef
    else:
        return []
    pairs = sorted(zip(names, values), key=lambda p: -p[1])[:top_n]
    return [{"feature": re.sub(r"^(num|cat)__", "", n), "importance": round(float(v), 5)} for n, v in pairs]


# ---------- persistence & prediction ----------

def list_models() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(models_dir().glob("*.json"))]


def load_model(name: str) -> tuple[Pipeline, dict]:
    name = _safe_name(name)
    path = models_dir() / f"{name}.joblib"
    if not path.exists():
        raise NotFoundError(f"Model '{name}' not found. Train one first.")
    meta = json.loads((models_dir() / f"{name}.json").read_text(encoding="utf-8"))
    return joblib.load(path), meta


def predict(name: str, records: list[dict[str, Any]]) -> dict:
    pipeline, meta = load_model(name)
    X = pd.DataFrame(records)
    for col in meta["features"]:
        if col not in X.columns:
            X[col] = np.nan  # missing inputs get imputed
    X = X[meta["features"]]
    out: dict[str, Any] = {"model": meta["name"], "task": meta["task"], "predictions": pipeline.predict(X).tolist()}
    if meta["task"] == "classification" and hasattr(pipeline, "predict_proba"):
        proba = pipeline.predict_proba(X)
        out["probabilities"] = [
            {str(c): round(float(p), 4) for c, p in zip(pipeline.classes_, row)} for row in proba
        ]
    return to_jsonable(out)


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:60] or "model"

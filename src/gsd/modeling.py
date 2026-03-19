from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def _group_metrics(
    group_values: pd.Series,
    y_true: pd.Series,
    y_pred: pd.Series,
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}

    for value in sorted(group_values.astype(str).unique()):
        mask = group_values.astype(str) == value
        y_true_group = y_true[mask]
        y_pred_group = y_pred[mask]

        metrics[value] = {
            "count": int(mask.sum()),
            "accuracy": float(accuracy_score(y_true_group, y_pred_group)),
            "precision_weighted": float(
                precision_score(y_true_group, y_pred_group, average="weighted", zero_division=0)
            ),
            "recall_weighted": float(
                recall_score(y_true_group, y_pred_group, average="weighted", zero_division=0)
            ),
            "f1_weighted": float(
                f1_score(y_true_group, y_pred_group, average="weighted", zero_division=0)
            ),
        }

    return metrics


def train_baseline_model(
    dataframe: pd.DataFrame,
    *,
    target_column: str,
    gender_column: str,
    include_gender_feature: bool = False,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[Pipeline, dict[str, Any]]:
    excluded_columns = [target_column]
    if not include_gender_feature:
        excluded_columns.append(gender_column)

    x = dataframe.drop(columns=excluded_columns)
    y = dataframe[target_column]
    groups = dataframe[gender_column].astype(str)

    if x.shape[1] == 0:
        raise ValueError("No usable features remain after dropping configured columns.")

    x_train, x_test, y_train, y_test, g_train, g_test = train_test_split(
        x,
        y,
        groups,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )

    numeric_features = x_train.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_features = [
        column for column in x_train.columns if column not in numeric_features
    ]

    transformers: list[tuple[str, Pipeline, list[str]]] = []

    if numeric_features:
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric_pipeline, numeric_features))

    if categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_features))

    if not transformers:
        raise ValueError("Unable to build feature transformers for the provided data.")

    model = Pipeline(
        steps=[
            ("preprocessor", ColumnTransformer(transformers=transformers)),
            (
                "classifier",
                LogisticRegression(max_iter=1000, class_weight="balanced"),
            ),
        ]
    )

    model.fit(x_train, y_train)
    y_pred = pd.Series(model.predict(x_test), index=y_test.index)

    metrics = {
        "overall": {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision_weighted": float(
                precision_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
            "recall_weighted": float(
                recall_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
            "f1_weighted": float(
                f1_score(y_test, y_pred, average="weighted", zero_division=0)
            ),
        },
        "by_gender": _group_metrics(g_test, y_test, y_pred),
        "n_train": int(len(x_train)),
        "n_test": int(len(x_test)),
        "target_column": target_column,
        "gender_column": gender_column,
        "include_gender_feature": include_gender_feature,
        "feature_columns": x.columns.tolist(),
    }

    return model, metrics

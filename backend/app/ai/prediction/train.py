"""
Training pipeline cho XGBoost classifier — predict warning risk.

Cách chạy:
  docker compose exec backend python -m app.ai.prediction.train

Output:
  data/models/xgboost_v1.pkl       — model
  data/models/feature_names.json   — feature order
  data/models/metrics_v1.json      — eval metrics
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import optuna
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from xgboost import XGBClassifier

from app.ai.prediction.features import (
    FEATURE_NAMES,
    MONOTONIC_CONSTRAINTS,
    extract_features_batch,
)
from app.db.session import AsyncSessionLocal

optuna.logging.set_verbosity(optuna.logging.WARNING)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "xgboost_v1.pkl"
FEATURES_PATH = MODEL_DIR / "feature_names.json"
METRICS_PATH = MODEL_DIR / "metrics_v1.json"

RANDOM_SEED = 42


async def load_dataset() -> tuple[pd.DataFrame, pd.Series]:
    """Load 1000 SV synthetic, extract features, return (X, y)."""
    print("[1/4] Loading synthetic students from DB...")
    async with AsyncSessionLocal() as db:
        ids, feats, labels = await extract_features_batch(db, only_synthetic=True)
    print(f"      {len(ids)} students loaded ({sum(labels)} positive, {sum(labels)/len(labels)*100:.1f}%)")

    print("[2/4] Building DataFrame...")
    X = pd.DataFrame(feats, columns=FEATURE_NAMES).astype(float)
    y = pd.Series(labels, name="is_warned").astype(int)
    return X, y


def make_objective(X_train: pd.DataFrame, y_train: pd.Series, scale_pos_weight: float):
    """Optuna objective: maximize F1 trên 5-fold CV."""
    def objective(trial: optuna.Trial) -> float:
        params: dict[str, Any] = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "n_estimators":     trial.suggest_int("n_estimators", 100, 400),
            "max_depth":        trial.suggest_int("max_depth", 3, 8),
            "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 6),
            "gamma":            trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha":        trial.suggest_float("reg_alpha", 0.0, 2.0),
            "reg_lambda":       trial.suggest_float("reg_lambda", 0.5, 5.0),
            "scale_pos_weight": scale_pos_weight,
            "monotone_constraints": tuple(MONOTONIC_CONSTRAINTS),
            "random_state":     RANDOM_SEED,
            "n_jobs":           -1,
            "verbosity":        0,
        }
        model = XGBClassifier(**params)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
        scores = cross_val_score(model, X_train, y_train, scoring="f1", cv=cv, n_jobs=1)
        return float(scores.mean())
    return objective


async def main(n_trials: int = 25):
    t0 = time.time()
    X, y = await load_dataset()

    n_pos = int(y.sum())
    n_neg = int((y == 0).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)
    print(f"      class balance: neg={n_neg}, pos={n_pos}, scale_pos_weight={scale_pos_weight:.2f}")

    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=RANDOM_SEED
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.176,
        stratify=y_temp, random_state=RANDOM_SEED
    )
    print(f"      train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    print(f"[3/4] Optuna tuning ({n_trials} trials, 5-fold CV)...")
    study = optuna.create_study(direction="maximize", study_name="xgb_warning")
    study.optimize(
        make_objective(X_train, y_train, scale_pos_weight),
        n_trials=n_trials,
        show_progress_bar=False,
    )
    print(f"      Best CV F1: {study.best_value:.4f}")
    print(f"      Best params: {study.best_params}")

    print("[4/4] Training final model + evaluating on test set...")
    final_params = {
        **study.best_params,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "tree_method": "hist",
        "scale_pos_weight": scale_pos_weight,
        "monotone_constraints": tuple(MONOTONIC_CONSTRAINTS),
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
        "verbosity": 0,
    }
    # Train on train set only first (để tune threshold trên val)
    model = XGBClassifier(**final_params)
    model.fit(X_train, y_train)

    # Tune decision threshold trên val để max F1
    val_proba = model.predict_proba(X_val)[:, 1]
    best_threshold = 0.5
    best_val_f1 = 0.0
    for thr in [t / 100 for t in range(20, 80, 2)]:
        val_pred = (val_proba >= thr).astype(int)
        f1 = f1_score(y_val, val_pred, zero_division=0)
        if f1 > best_val_f1:
            best_val_f1 = f1
            best_threshold = thr
    print(f"      Tuned threshold: {best_threshold:.2f} (val F1={best_val_f1:.4f})")

    # Retrain on train+val with same params
    X_trainval = pd.concat([X_train, X_val])
    y_trainval = pd.concat([y_train, y_val])
    model = XGBClassifier(**final_params)
    model.fit(X_trainval, y_trainval)

    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= best_threshold).astype(int)

    metrics = {
        "accuracy":  float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall":    float(recall_score(y_test, y_pred, zero_division=0)),
        "f1":        float(f1_score(y_test, y_pred, zero_division=0)),
        "auc_roc":   float(roc_auc_score(y_test, y_proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
        "best_cv_f1": float(study.best_value),
        "best_params": study.best_params,
        "decision_threshold": best_threshold,
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
        "scale_pos_weight": scale_pos_weight,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "training_seconds": round(time.time() - t0, 2),
    }

    print("\n=== Test Set Metrics ===")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1:        {metrics['f1']:.4f}")
    print(f"  AUC-ROC:   {metrics['auc_roc']:.4f}")
    print(f"  Confusion: {metrics['confusion_matrix']}")

    joblib.dump(model, MODEL_PATH)
    with open(FEATURES_PATH, "w") as f:
        json.dump(FEATURE_NAMES, f, indent=2)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    size_mb = MODEL_PATH.stat().st_size / 1024 / 1024
    print(f"\n✓ Saved to {MODEL_DIR}/ ({size_mb:.2f} MB)")
    print(f"  Total time: {metrics['training_seconds']}s")

    if metrics["f1"] >= 0.8:
        print(f"\n🎯 F1 = {metrics['f1']:.4f} ≥ 0.8 — TARGET MET")
    else:
        print(f"\n⚠️  F1 = {metrics['f1']:.4f} < 0.8 — under target")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    asyncio.run(main(n))

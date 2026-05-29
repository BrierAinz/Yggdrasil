"""
Lilith 3.0 — Entrenamiento del clasificador local de intención (Fase 4).
Usa TfidfVectorizer + LogisticRegression sobre el CSV message,tool_name.
Guarda el pipeline con joblib en memory/episodic/intent_classifier.joblib.
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def train_and_save(
    csv_path: Path,
    model_path: Path,
    max_features: int = 5000,
    max_iter: int = 500,
) -> tuple[int, list[str]]:
    """
    Entrena un pipeline TF-IDF + LogisticRegression y lo guarda.
    Devuelve (número de muestras, lista de clases).
    """
    if not csv_path.exists():
        return 0, []
    df = pd.read_csv(csv_path, encoding="utf-8")
    if df.empty or "message" not in df.columns or "tool_name" not in df.columns:
        return 0, []
    X = df["message"].fillna("").astype(str)
    y = df["tool_name"].fillna("generate_reply").astype(str)
    if len(X) < 5:
        return len(X), []
    vectorizer = TfidfVectorizer(
        max_features=max_features, ngram_range=(1, 2), min_df=1
    )
    clf = LogisticRegression(max_iter=max_iter, random_state=42)
    pipeline = Pipeline([("tfidf", vectorizer), ("clf", clf)])
    pipeline.fit(X, y)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    classes = list(pipeline.named_steps["clf"].classes_)
    joblib.dump({"pipeline": pipeline, "classes": classes}, model_path)
    return len(X), classes


def main() -> None:
    base = Path(__file__).resolve().parent.parent.parent.parent
    if len(sys.argv) > 1:
        base = Path(sys.argv[1])
    csv_path = base / "memory" / "episodic" / "dataset_train.csv"
    model_path = base / "memory" / "episodic" / "intent_classifier.joblib"
    if len(sys.argv) > 2:
        csv_path = Path(sys.argv[2])
    if len(sys.argv) > 3:
        model_path = Path(sys.argv[3])
    n, classes = train_and_save(csv_path, model_path)
    print(f"Entrenado con {n} muestras. Clases: {classes}")
    print(f"Modelo guardado en {model_path}")


if __name__ == "__main__":
    main()

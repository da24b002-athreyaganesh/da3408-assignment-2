"""Train a TF-IDF + MultinomialNB spam classifier and persist it with joblib.

Run at IMAGE BUILD TIME so the container starts with a ready model and the
training-only dependencies (pandas, the CSV) never have to ship in the runtime
image.
"""
import argparse

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="spam_dataset.csv")
    parser.add_argument("--out", default="model.joblib")
    args = parser.parse_args()

    df = pd.read_csv(args.data)
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2))),
            ("nb", MultinomialNB()),
        ]
    )
    pipeline.fit(X_train, y_train)

    acc = accuracy_score(y_test, pipeline.predict(X_test))
    print(f"Holdout accuracy: {acc:.4f}")

    joblib.dump(pipeline, args.out)
    print(f"Saved model to {args.out}")


if __name__ == "__main__":
    main()

"""
Trains a tiny, CPU-friendly sentiment classifier.
TF-IDF + Logistic Regression on a small hand-labeled dataset.
This is intentionally lightweight - the goal of this project is
Kubernetes/MLOps, not state-of-the-art NLP.
"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

POSITIVE = [
    "I really love this product", "This is absolutely amazing",
    "Great experience, highly recommend", "Excellent quality and fast shipping",
    "This made my day, wonderful", "Fantastic service, will buy again",
    "I am so happy with this purchase", "Best thing I bought this year",
    "Works perfectly, very satisfied", "Superb design and great value",
    "This exceeded my expectations", "Amazing customer support",
    "I love how easy this is to use", "Pretty good, I'm impressed",
    "Totally worth the money", "Wonderful experience overall",
]
NEGATIVE = [
    "I hate this product", "This is absolutely terrible",
    "Worst experience ever", "Poor quality and slow shipping",
    "This ruined my day, awful", "Terrible service, never again",
    "I am so disappointed with this purchase", "Worst thing I bought this year",
    "Does not work, very frustrated", "Bad design and overpriced",
    "This fell short of my expectations", "Horrible customer support",
    "This is confusing and hard to use", "Pretty bad, I'm unimpressed",
    "Total waste of money", "Awful experience overall",
]

texts = POSITIVE + NEGATIVE
labels = [1] * len(POSITIVE) + [0] * len(NEGATIVE)

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
    ("clf", LogisticRegression(max_iter=1000)),
])
pipeline.fit(texts, labels)

out_path = os.path.join(os.path.dirname(__file__), "sentiment_model.joblib")
joblib.dump(pipeline, out_path)
print(f"Sentiment model trained and saved to {out_path}")

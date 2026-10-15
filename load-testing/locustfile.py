"""
Load test for ModelForge's API Gateway.

Usage (from repo root, gateway reachable e.g. via `minikube service` or
port-forward at http://localhost:8000, or through the Ingress host):

    pip install -r load-testing/requirements.txt
    locust -f load-testing/locustfile.py --host http://modelforge.local

Then open http://localhost:8089 to control the test and watch RPS/latency,
while in another terminal you run:

    kubectl get hpa -n modelforge --watch

to watch replicas scale up under load.
"""
import random
from locust import HttpUser, task, between

SENTIMENT_SAMPLES = [
    "This product is absolutely amazing!",
    "I really don't like how this works.",
    "Best purchase I've made all year.",
    "Terrible experience, would not recommend.",
    "Pretty good overall, minor issues.",
]


class ModelForgeUser(HttpUser):
    wait_time = between(0.1, 1.0)

    @task(3)
    def predict_sentiment(self):
        payload = {"text": random.choice(SENTIMENT_SAMPLES)}
        self.client.post("/api/v1/predict/sentiment", json=payload, name="/predict/sentiment")

    @task(2)
    def predict_regression(self):
        payload = {
            "features": [
                random.uniform(500, 4000),
                random.randint(1, 5),
                random.randint(1, 3),
                random.uniform(0, 40),
            ]
        }
        self.client.post("/api/v1/predict/regression", json=payload, name="/predict/regression")

    @task(1)
    def list_models(self):
        self.client.get("/api/v1/models", name="/models")

    @task(1)
    def check_health(self):
        self.client.get("/health", name="/health")

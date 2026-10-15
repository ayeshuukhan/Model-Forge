# ModelForge 

ModelForge is a portfolio-grade DevOps/MLOps project that deploys three
independent machine-learning models as microservices behind an API
Gateway, orchestrated with Kubernetes. The ML models are intentionally
lightweight (CPU-only, no GPU) — **the learning objective is Kubernetes
and cloud-native architecture**, not state-of-the-art ML.

## Overview

A client sends an inference request naming a model (`sentiment`, `image`,
or `regression`) to the API Gateway. The Gateway validates the request,
records it in PostgreSQL, forwards it to the correct model service via
Kubernetes Service discovery, publishes an async event to Redis, and
returns the prediction. Everything runs in its own container, its own
Kubernetes Deployment, and scales independently via Horizontal Pod
Autoscalers (HPA).

## Architecture

```text
                       USER / CLIENT
                             |
                             v
                     (modelforge.local)
                             |
                             v
                       API GATEWAY  (FastAPI, HPA: 2-5 pods)
                             |
             +---------------+---------------+
             |               |               |
             v               v               v
       SENTIMENT         IMAGE MODEL      REGRESSION
        SERVICE            SERVICE          SERVICE
       (HPA: 2-5)          (1 pod)          (1 pod)
             |               |               |
             +---------------+---------------+
                             |
                    Redis (async event log)
                             |
                             v
                PostgreSQL (inference_requests table, PVC-backed)
                             |
                             v
                  Prometheus  --->  Grafana
```

Each model service is a separate FastAPI app, in its own Docker image,
deployed as its own Kubernetes Deployment + Service — so it can be
scaled, updated, or replaced without touching the others.

## Why Kubernetes?

This project uses Kubernetes to solve real problems that show up the
moment you have more than one service:

- **Service discovery** — the API Gateway calls `http://sentiment-service`,
  never a pod IP. Kubernetes DNS resolves the Service name to whichever
  healthy pod should handle it, even as pods are replaced.
- **Self-healing** — liveness probes let Kubernetes restart a pod that's
  stuck; readiness probes stop traffic reaching a pod before it's ready.
- **Horizontal scaling** — HPA watches CPU utilization and adds/removes
  pods automatically under load, instead of manually provisioning
  capacity for peak traffic.
- **Configuration separation** — ConfigMaps/Secrets keep environment
  config and credentials out of the container image, so the same image
  runs in dev/staging/prod with different config.
- **Persistent storage** — a PVC keeps PostgreSQL's data alive across
  pod restarts, which a plain container filesystem would not.
- **Declarative infrastructure** — the whole platform's desired state
  lives in YAML (or a Helm chart), so `kubectl apply -f kubernetes/`
  reproduces the entire system from scratch.

### How Kubernetes Service discovery works here

Every Deployment has a matching `Service` (ClusterIP). Kubernetes runs
an internal DNS server (CoreDNS) that resolves a Service's name (e.g.
`sentiment-service`) to a stable virtual IP, which `kube-proxy` load
balances across all healthy pods behind it. The API Gateway never needs
to know a pod's IP address — it just calls `http://sentiment-service`
(same namespace) and Kubernetes handles routing and load balancing,
even as pods are created, destroyed, or rescheduled.

## Technology Stack

| Component        | Technology                          | Why |
|-------------------|--------------------------------------|-----|
| API Gateway       | FastAPI + httpx                     | async, fast, easy request validation |
| Model services    | FastAPI + scikit-learn               | lightweight, CPU-only, fast to containerize |
| Database          | PostgreSQL + SQLAlchemy + Alembic    | durable inference history, versioned schema |
| Queue/events      | Redis Streams                        | async, decoupled event logging |
| Containers        | Docker (multi-stage-friendly slim images) | reproducible builds |
| Orchestration     | Kubernetes                           | scaling, self-healing, service discovery |
| Ingress           | NGINX Ingress Controller             | single external entry point |
| Autoscaling       | Horizontal Pod Autoscaler            | scale on real CPU load |
| Monitoring        | Prometheus + Grafana                 | metrics collection + dashboards |
| Load testing      | Locust                               | generates real traffic to trigger HPA |
| Packaging         | Helm                                 | parameterized, reusable deployment |

## Project Structure

```text
modelforge/
├── api-gateway/            FastAPI gateway: routing, DB, Redis, metrics
├── models/
│   ├── sentiment/           TF-IDF + LogisticRegression service
│   ├── image/                Color/texture feature + RandomForest service
│   └── regression/           LinearRegression house-price service
├── database/migrations/     (Alembic migrations live in api-gateway/alembic)
├── kubernetes/               Raw K8s manifests (namespace, configmap, secret,
│                              ingress, per-service deploy/svc, hpa/)
├── monitoring/               Prometheus config + Grafana provisioning/dashboard
├── load-testing/             Locustfile
├── helm/modelforge/          Helm chart wrapping all of the above
├── docker-compose.yml        Local dev stack
├── .env.example
└── README.md
```

## Local Development (Docker Compose)

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```
2. Build and start everything:
   ```bash
   docker compose up --build
   ```
3. The API Gateway is now at `http://localhost:8000`.

Send a test request:
```bash
curl -X POST http://localhost:8000/api/v1/predict/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is absolutely amazing!"}'
```

## Kubernetes Deployment

Requires: Docker, `kubectl`, Minikube (or Kind), Helm (optional), and the
Kubernetes Metrics Server (needed for HPA to read CPU usage).

### 1. Start the cluster

```bash
minikube start --cpus=4 --memory=6144
minikube addons enable ingress
minikube addons enable metrics-server
```

### 2. Build the images inside Minikube's Docker daemon

```bash
eval $(minikube docker-env)

docker build -t modelforge/api-gateway:latest ./api-gateway
docker build -t modelforge/sentiment-service:latest ./models/sentiment
docker build -t modelforge/image-service:latest ./models/image
docker build -t modelforge/regression-service:latest ./models/regression
```

### 3. Deploy

```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/postgres/
kubectl apply -f kubernetes/redis/
kubectl apply -f kubernetes/sentiment/
kubectl apply -f kubernetes/image/
kubectl apply -f kubernetes/regression/
kubectl apply -f kubernetes/api-gateway/
kubectl apply -f kubernetes/hpa/
kubectl apply -f kubernetes/ingress.yaml
kubectl apply -f monitoring/prometheus/k8s.yaml
kubectl apply -f monitoring/grafana/k8s.yaml
```

(Or simply `kubectl apply -R -f kubernetes/ -f monitoring/` once the
namespace/configmap/secret exist.)

### 4. Configure local hostname resolution

```bash
echo "$(minikube ip) modelforge.local" | sudo tee -a /etc/hosts
```

On Windows, edit `C:\Windows\System32\drivers\etc\hosts` as Administrator
and add the same line using the IP from `minikube ip`.

## Verification

```bash
kubectl get pods -n modelforge
kubectl get services -n modelforge
kubectl get deployments -n modelforge
kubectl get hpa -n modelforge
kubectl get pvc -n modelforge
```

All pods should show `Running` and `1/1` (or `2/2`) ready.

## Testing

```bash
curl http://modelforge.local/health
curl http://modelforge.local/api/v1/models

curl -X POST http://modelforge.local/api/v1/predict/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "I really love this product."}'

curl -X POST http://modelforge.local/api/v1/predict/regression \
  -H "Content-Type: application/json" \
  -d '{"features": [1200, 3, 2, 10]}'

curl -X POST http://modelforge.local/api/v1/predict/image \
  -F "file=@/path/to/some_image.jpg"

curl http://modelforge.local/api/v1/stats
```

## Autoscaling Demo

1. Watch replicas in one terminal:
   ```bash
   kubectl get hpa -n modelforge --watch
   ```
2. Generate load in another terminal:
   ```bash
   pip install -r load-testing/requirements.txt
   locust -f load-testing/locustfile.py --host http://modelforge.local
   ```
   Open `http://localhost:8089`, set e.g. 200 users / spawn rate 20, and start.
3. Watch `api-gateway-hpa` and `sentiment-service-hpa` CPU utilization climb
   and replicas increase from 2 toward 5, then scale back down a minute or
   so after load stops (`stabilizationWindowSeconds: 60` on scale-down).

This is real autoscaling driven by real CPU load — not a scripted demo.

## Monitoring

```bash
kubectl port-forward -n modelforge svc/prometheus-service 9090:9090
kubectl port-forward -n modelforge svc/grafana-service 3000:3000
```

- Prometheus UI: `http://localhost:9090`
- Grafana UI: `http://localhost:3000` (user: `admin`, password: value of
  `GRAFANA_ADMIN_PASSWORD` in `kubernetes/secret.yaml`)

Import `monitoring/grafana/modelforge-dashboard.json` in Grafana (or rely
on the provisioning config) to see request rates, latency percentiles,
error rates, and pod counts per deployment.

## Helm (optional, after raw manifests work)

```bash
helm install modelforge ./helm/modelforge --namespace modelforge --create-namespace
# upgrade after changes:
helm upgrade modelforge ./helm/modelforge --namespace modelforge
# uninstall:
helm uninstall modelforge --namespace modelforge
```

Override any value, e.g.:
```bash
helm install modelforge ./helm/modelforge \
  --set postgres.password=some-strong-password \
  --set apiGateway.maxReplicas=8
```

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `CrashLoopBackOff` | Check `kubectl logs -n modelforge <pod>`; usually a missing env var, bad DB connection string, or the app crashing on startup. |
| `ImagePullBackOff` | Image wasn't built inside Minikube's Docker daemon (`eval $(minikube docker-env)`), or `imagePullPolicy` isn't `IfNotPresent`. |
| PVC stuck `Pending` | No default StorageClass in the cluster. Run `kubectl get storageclass`; Minikube ships one (`standard`) by default. |
| Ingress unreachable | Confirm `minikube addons enable ingress`, confirm `/etc/hosts` entry matches `minikube ip`, confirm Ingress controller pod is `Running` in `ingress-nginx` namespace. |
| HPA shows `<unknown>` for CPU | Metrics Server isn't installed/ready: `minikube addons enable metrics-server`, wait ~1 min. |
| Service connection failure (gateway can't reach model service) | Check the Service name matches the env var in the ConfigMap exactly, and that the target Deployment's pod is `Ready`. |
| Database connection failure | Check `POSTGRES_HOST`/credentials in ConfigMap/Secret match the postgres Service name and Secret keys; check `kubectl logs -n modelforge deploy/postgres`. |

## Security Notes

- No PostgreSQL/Redis Service is exposed outside the cluster (no
  NodePort/LoadBalancer, no Ingress rule) — only ClusterIP.
- Credentials live in a Kubernetes Secret, never hard-coded or committed
  as plaintext (`secret.yaml` here uses **placeholder** base64 values —
  replace before any real deployment).
- Containers run as a non-root user where practical.
- Request sizes are capped (JSON body limit, 5MB image upload limit) to
  reduce abuse surface.
- Internal stack traces are never returned to clients — a global
  exception handler returns a generic 500.
- Authentication is intentionally out of scope so it doesn't distract
  from the Kubernetes learning objectives; see "Next Steps" below.

## Next Steps (not implemented, left as extensions)

- Add API-key or JWT authentication at the Ingress or Gateway layer.
- Add NetworkPolicies to restrict which pods can talk to Postgres/Redis.
- Add a CI/CD pipeline (build → push → `helm upgrade`).
- Replace the RandomForest image classifier with a real pretrained CNN
  once GPU/registry constraints aren't a concern.

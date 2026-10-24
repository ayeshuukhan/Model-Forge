### What You Need Installed

- Docker Desktop
- kubectl
- Minikube
- Python (for Locust, the load-testing tool)

### You Will Open 5 Terminal Windows

Each terminal has one job. Don't close them once they're running,
except where noted.

| Terminal | Purpose | Keep Running? |
|---|---|---|
| 1 | Starts the cluster, forwards the API to your browser | Yes |
| 2 | Shows autoscaling happening live | Yes |
| 3 | Used to run test commands and take screenshots | Close anytime |
| 4 | Runs the load-testing tool (Locust) | Yes, while testing |
| 5 | Forwards Grafana (the monitoring dashboard) to your browser | Yes, while viewing it |

In every terminal, start by moving into the project folder:

```powershell
cd C:\---
```

---

### Terminal 1 — Start the Cluster

```powershell
minikube start
```

Wait until it says "Done!" (this can take 1–2 minutes).

Check that everything deployed correctly:

```powershell
kubectl get pods -n modelforge
```

Every row should say `Running`. If something looks broken (especially
the `postgres` pod restarting many times), see the Troubleshooting
section below before continuing.

Now, in this same terminal, start the connection that lets your
browser talk to the API:

```powershell
kubectl port-forward -n modelforge svc/api-gateway-service 8080:80
```

You'll see a line like `Forwarding from 127.0.0.1:8080 -> 8000` and it
will stay there. That's correct — leave this terminal open and don't
type anything else into it.

### Terminal 2 — Watch Autoscaling Live

Open a new PowerShell window:

```powershell
kubectl get hpa -n modelforge --watch
```

This will sit and update automatically whenever the system scales up
or down. Leave it open.

### Terminal 3 — Test the API

Open a new PowerShell window. Run these one at a time to confirm
everything works:

```powershell
Invoke-WebRequest http://localhost:8080/health -UseBasicParsing | Select-Object -ExpandProperty Content
```
Should return: `{"status":"ok"}`

```powershell
Invoke-WebRequest -Uri http://localhost:8080/api/v1/predict/sentiment -Method POST -ContentType "application/json" -Body '{"text": "This project works great!"}' -UseBasicParsing | Select-Object -ExpandProperty Content
```
Should return a prediction with a sentiment and confidence score.

```powershell
Invoke-WebRequest -Uri http://localhost:8080/api/v1/predict/regression -Method POST -ContentType "application/json" -Body '{"features": [1200, 3, 2, 10]}' -UseBasicParsing | Select-Object -ExpandProperty Content
```
Should return a predicted price.

```powershell
Invoke-WebRequest http://localhost:8080/api/v1/stats -UseBasicParsing | Select-Object -ExpandProperty Content
```
Should show a summary of all requests made so far.

You can also check the infrastructure itself:

```powershell
kubectl get pods -n modelforge
kubectl get svc -n modelforge
kubectl get hpa -n modelforge
kubectl get deployments -n modelforge
kubectl get pvc -n modelforge
```

### Terminal 4 — Run a Load Test 

Open a new PowerShell window:

```powershell
locust -f load-testing/locustfile.py --host http://localhost:8080
```

Open your browser to `http://localhost:8089`. Fill in:

- Number of users: `40`
- Ramp up: `5`
- Click **Start swarming**

Within a minute, watch Terminal 2 — the `REPLICAS` number should climb
from 2 toward 4 or 5 as CPU usage rises. This is the system scaling
itself automatically under load. When you're done, click **Stop** in
the Locust browser tab.

### Terminal 5 — View the Monitoring Dashboard (Grafana)

Open a new PowerShell window:

```powershell
kubectl port-forward -n modelforge svc/grafana-service 3000:3000
```

Open your browser to `http://localhost:3000`.
Log in with username `admin` and password `admin-change-me`.

Go to **Dashboards → ModelForge Overview**. If it's not there yet,
import it manually: click **New → Import**, upload
`monitoring\grafana\modelforge-dashboard.json`, choose **Prometheus**
as the data source, and click **Import**.

Set the time range (top right) to **Last 15 minutes** and refresh to
**10s** so it updates live. The graphs will only show data if you ran
a load test recently — if it says "No data," that's normal until
traffic goes through the system.

### Shutting Everything Down

When you're finished, press `Ctrl+C` in the Locust and port-forward
terminals, then run:

```powershell
minikube stop
```

Nothing is deleted — next time you run `minikube start`, everything
comes back as it was.

### Troubleshooting

| Problem | What It Means | Fix |
|---|---|---|
| `Unable to connect to the remote server` on localhost:8080 | The port-forward in Terminal 1 disconnected | Re-run `kubectl port-forward -n modelforge svc/api-gateway-service 8080:80` |
| Postgres pod restarting repeatedly | Its data got corrupted during an earlier crash | Delete and recreate it: <br>`kubectl delete -f kubernetes/postgres/deployment.yaml`<br>`kubectl delete -f kubernetes/postgres/pvc.yaml`<br>(wait for the PVC to disappear)<br>`kubectl apply -f kubernetes/postgres/pvc.yaml`<br>`kubectl apply -f kubernetes/postgres/deployment.yaml` |
| All pods show `Unknown` | The laptop went to sleep and Kubernetes lost track of them | `minikube stop` then `minikube start` |
| Locust shows 100% failures | Same port-forward issue as above | Fix the port-forward, then click Reset and Start again in Locust |
| Grafana panel shows a red warning triangle | Prometheus isn't deployed | `kubectl apply -f monitoring/prometheus/k8s.yaml` |

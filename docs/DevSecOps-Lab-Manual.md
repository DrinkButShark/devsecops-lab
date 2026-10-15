# DevSecOps + GitOps + Kubernetes Security Lab

## Author

Hein Wai Yan Ko

---

# 1. Executive Summary

This lab demonstrates a complete DevSecOps pipeline from code commit to Kubernetes deployment.

Technologies:

- GitHub
- GitHub Actions
- Gitleaks
- Semgrep
- Trivy
- Docker
- GitHub Container Registry (GHCR)
- Syft (SBOM)
- Cosign
- ArgoCD
- Kubernetes (Kind)
- Kyverno

---

# 2. Architecture

```text
Developer
    │
    ▼
GitHub Repository
    │
    ▼
GitHub Actions
    │
    ├── Gitleaks
    ├── Semgrep
    ├── Trivy
    ├── Docker Build
    ├── SBOM (Syft)
    └── Cosign Sign
    │
    ▼
GHCR
    │
    ▼
ArgoCD
    │
    ▼
Kubernetes (Kind)
    │
    ▼
Kyverno
    │
    ▼
Application
```

---

# 3. Prerequisites

## Verify Environment

```bash
docker --version
git --version
kubectl version
kind version
gh --version
helm version
```

---

# 4. Create Kubernetes Cluster

```bash
kind create cluster --name devsecops
```

Verify:

```bash
kubectl get nodes
```

Expected:

```text
devsecops-control-plane Ready
```

---

# 5. Create Application

## app.py

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "DevSecOps Lab"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

## requirements.txt

```txt
flask==3.0.3
Werkzeug==3.1.3
```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

---

# 6. Build Docker Image

```bash
docker build -t devsecops-demo:v1 .
```

Run:

```bash
docker run -d \
--name devsecops-demo \
-p 5000:5000 \
devsecops-demo:v1
```

Test:

```bash
curl localhost:5000
```

Expected:

```text
DevSecOps Lab
```

---

# 7. GitHub Repository

```bash
git init

git branch -M main

git remote add origin \
git@github.com:DrinkButShark/devsecops-lab.git
```

Push:

```bash
git add .
git commit -m "initial commit"
git push -u origin main
```

---

# 8. GitHub Actions Workflows

## hello.yml

```yaml
name: Hello DevSecOps

on:
  push:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - run: echo "DevSecOps Pipeline Running"
```

---

# 9. Secret Scanning - Gitleaks

## gitleaks.yml

```yaml
name: Gitleaks

on:
  push:
  pull_request:

jobs:
  gitleaks:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: gitleaks/gitleaks-action@v2
```

---

## Secret Detection Test

```txt
AWS_SECRET_ACCESS_KEY=test123
```

Expected:

```text
Pipeline Failed
```

---

# 10. Static Code Scan - Semgrep

## semgrep.yml

```yaml
name: Semgrep

on:
  push:
  pull_request:

jobs:
  semgrep:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit
```

---

## Vulnerable Example

```python
import subprocess

subprocess.run(user_input, shell=True)
```

Expected:

```text
Command Injection Finding
```

---

# 11. Vulnerability Scanning - Trivy

## trivy.yml

```yaml
name: Trivy

on:
  push:

jobs:
  trivy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scan-ref: .
```

---

# 12. Build and Push Image

## build.yml

```yaml
name: Build and Push Image

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: ./app
          push: true
          tags: ghcr.io/drinkbutshark/devsecops-lab:latest
```

---

# 13. SBOM Generation

## sbom.yml

```yaml
name: SBOM

on:
  push:

jobs:
  sbom:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install Syft
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh

      - name: Generate SBOM
        run: |
          syft ghcr.io/drinkbutshark/devsecops-lab:latest \
            -o spdx-json > sbom.json
```

---

# 14. Cosign Signing

Generate key:

```bash
cosign generate-key-pair
```

Files:

```text
cosign.key
cosign.pub
```

GitHub Secrets:

```text
COSIGN_PRIVATE_KEY
COSIGN_PASSWORD
```

---

## sign.yml

```yaml
name: Sign Image

on:
  push:

jobs:
  sign:
    runs-on: ubuntu-latest

    permissions:
      packages: write

    steps:

      - uses: sigstore/cosign-installer@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Sign Image
        env:
          COSIGN_PRIVATE_KEY: ${{ secrets.COSIGN_PRIVATE_KEY }}
          COSIGN_PASSWORD: ${{ secrets.COSIGN_PASSWORD }}
        run: |
          echo "$COSIGN_PRIVATE_KEY" > cosign.key

          cosign sign \
            --yes \
            --key cosign.key \
            ghcr.io/drinkbutshark/devsecops-lab:latest
```

---

# 15. Install ArgoCD

```bash
kubectl create namespace argocd
```

```bash
kubectl apply -n argocd \
-f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

---

## Get Password

```bash
kubectl -n argocd get secret \
argocd-initial-admin-secret \
-o jsonpath="{.data.password}" | base64 -d
```

---

# 16. GitOps Deployment

## app.yaml

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application

metadata:
  name: devsecops-demo
  namespace: argocd

spec:
  project: default

  source:
    repoURL: https://github.com/DrinkButShark/devsecops-lab.git
    path: gitops
    targetRevision: main

  destination:
    server: https://kubernetes.default.svc
    namespace: default

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

---

# 17. GHCR Authentication

## Create Pull Secret

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=DrinkButShark \
  --docker-password=<PAT> \
  --docker-email=heinwaiyanko1@gmail.com
```

---

# 18. Kubernetes Deployment

## deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: devsecops-demo

spec:
  replicas: 2

  selector:
    matchLabels:
      app: devsecops-demo

  template:
    metadata:
      labels:
        app: devsecops-demo

    spec:

      imagePullSecrets:
      - name: ghcr-secret

      containers:
      - name: devsecops-demo
        image: ghcr.io/drinkbutshark/devsecops-lab:latest

        ports:
        - containerPort: 5000
```

---

# 19. Troubleshooting

## Git Push Rejected

```text
main -> main rejected
```

Fix:

```bash
git pull origin main \
--allow-unrelated-histories
```

---

## Invalid Workflow

```text
Invalid workflow file
```

Fix YAML indentation.

---

## Gitleaks Failure

```text
private-key detected
```

Fix:

```bash
git rm --cached cosign.key
```

---

## GHCR Build Failure

```text
repository name must be lowercase

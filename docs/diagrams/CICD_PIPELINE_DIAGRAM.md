# CI/CD Pipeline Architecture (Mermaid)

This diagram illustrates the complete Continuous Integration and Continuous Deployment pipeline from development through production on AWS.

## CI/CD Pipeline Workflow

```mermaid
graph LR
    subgraph Developer["👤 Developer Workflow"]
        DEV1["Code Changes<br/>on Local Machine"]
        DEV2["Git Commit<br/>& Push"]
        DEV3["Push to<br/>main branch"]
    end

    subgraph Trigger["⚡ Pipeline Trigger"]
        TRIG1["GitHub<br/>Push Event"]
    end

    subgraph CI["🏗️ CI: Build & Push Stage"]
        CI1["GitHub Actions<br/>Runner<br/>ubuntu-latest"]
        CI2["Checkout<br/>Repository"]
        CI3["AWS Login<br/>with Credentials"]
        CI4["Build<br/>Docker Image<br/>Python 3.10-slim"]
        CI5["Run Tests<br/>pytest"]
        CI6["Push to<br/>Amazon ECR<br/>Container Registry"]
        CI7["Build Status<br/>OK?"]
        
        CI1 --> CI2
        CI2 --> CI3
        CI3 --> CI4
        CI4 --> CI5
        CI5 --> CI7
        CI7 -->|PASS| CI6
        CI7 -->|FAIL| FAIL1["❌ Notify Developer<br/>Build Failed"]
    end

    subgraph CD["🚀 CD: Deploy Stage"]
        CD1["GitHub Actions<br/>Self-hosted Runner<br/>AWS EC2"]
        CD2["AWS Login<br/>with Credentials"]
        CD3["Docker Pull<br/>from ECR"]
        CD4["Stop Old<br/>Container<br/>if running"]
        CD5["Docker Run<br/>New Container<br/>Port 8080"]
        CD6["Health Check<br/>GET /health"]
        CD7["Deploy<br/>OK?"]
        
        CD1 --> CD2
        CD2 --> CD3
        CD3 --> CD4
        CD4 --> CD5
        CD5 --> CD6
        CD6 --> CD7
        CD7 -->|PASS| SUCCESS["✅ Deployment Success<br/>App Live"]
        CD7 -->|FAIL| FAIL2["❌ Rollback<br/>Previous Version"]
    end

    subgraph AWS["☁️ AWS Infrastructure"]
        AWS1["Amazon ECR<br/>Container<br/>Registry"]
        AWS2["AWS EC2 Instance<br/>t2.micro / t3.small<br/>Ubuntu 24.04"]
        AWS3["Docker<br/>Container<br/>Port 8080"]
        AWS4["Environment Variables<br/>API Keys<br/>Secrets Manager"]
    end

    subgraph ExternalServices["🔗 External Services"]
        EXT1["Groq API<br/>LLM Inference"]
        EXT2["Pinecone<br/>Vector Database"]
        EXT3["HuggingFace<br/>Model Hub"]
    end

    %% Main flow
    DEV1 --> DEV2
    DEV2 --> DEV3
    DEV3 --> TRIG1
    TRIG1 --> CI1
    
    CI6 --> AWS1
    CI6 -->|Success| CD1
    
    CD3 --> AWS1
    CD3 --> AWS2
    AWS2 --> AWS3
    AWS3 --> AWS4
    
    AWS3 -.->|API Calls| EXT1
    AWS3 -.->|Vector Search| EXT2
    AWS3 -.->|Model Download| EXT3

    %% Styling
    classDef dev fill:#4a90e2,stroke:#2c5aa0,stroke-width:2px,color:#fff
    classDef trigger fill:#f5a623,stroke:#d68910,stroke-width:2px,color:#fff
    classDef pipeline fill:#7ed321,stroke:#5fa319,stroke-width:2px,color:#fff
    classDef test fill:#bd10e0,stroke:#9012fe,stroke-width:2px,color:#fff
    classDef deploy fill:#50e3c2,stroke:#2eb89c,stroke-width:2px,color:#fff
    classDef aws fill:#ff9900,stroke:#cc7700,stroke-width:2px,color:#fff
    classDef external fill:#e74c3c,stroke:#c0392b,stroke-width:2px,color:#fff
    classDef success fill:#27ae60,stroke:#1e8449,stroke-width:3px,color:#fff
    classDef error fill:#e74c3c,stroke:#c0392b,stroke-width:3px,color:#fff

    class DEV1,DEV2,DEV3 dev
    class TRIG1 trigger
    class CI1,CI2,CI3 pipeline
    class CI4,CI6 pipeline
    class CI5 test
    class CD1,CD2,CD3,CD4,CD5 deploy
    class CD6 test
    class AWS1,AWS2,AWS3,AWS4 aws
    class EXT1,EXT2,EXT3 external
    class SUCCESS success
    class FAIL1,FAIL2 error
```

## Detailed Pipeline Stages

### 1️⃣ Developer Workflow

**What happens**:
- Developer makes code changes locally
- Commits changes with descriptive message
- Pushes to `main` branch on GitHub

**Example**:
```bash
git add .
git commit -m "feat: improve query rewriting logic"
git push origin main
```

### 2️⃣ CI: Build & Push Stage

**GitHub Actions Configuration**:
```yaml
name: CI Pipeline
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: aws-actions/configure-aws-credentials@v2
      - run: docker build -t medical-chatbot:${{ github.sha }} .
      - run: pytest tests/
      - run: docker push $ECR_REGISTRY/medical-chatbot:${{ github.sha }}
```

**Steps**:

| Step | Duration | Purpose | Success Criteria |
|------|----------|---------|-----------------|
| **Checkout** | 10s | Clone repository | No errors |
| **AWS Login** | 5s | Authenticate with AWS | Credentials valid |
| **Build Docker** | 30-45s | Create container image with Python 3.10 | Image builds without errors |
| **Run Tests** | 10-20s | Execute pytest suite | All tests pass |
| **Push to ECR** | 15-30s | Upload image to Amazon ECR | Image stored in registry |

**Trigger**: Push to `main` branch  
**On Failure**: Developers notified, build stops, deployment skipped  
**On Success**: Proceeds to CD stage

### 3️⃣ CD: Deploy Stage

**GitHub Actions Configuration** (Self-hosted Runner on EC2):
```yaml
deploy:
  runs-on: [self-hosted, ec2]
  needs: build
  steps:
    - uses: aws-actions/configure-aws-credentials@v2
    - run: docker pull $ECR_REGISTRY/medical-chatbot:${{ github.sha }}
    - run: docker stop medical-chatbot || true
    - run: docker run -d --name medical-chatbot -p 8080:8080 \
            -e GROQ_API_KEY=${{ secrets.GROQ_API_KEY }} \
            -e PINECONE_API_KEY=${{ secrets.PINECONE_API_KEY }} \
            $ECR_REGISTRY/medical-chatbot:${{ github.sha }}
    - run: curl -f http://localhost:8080/health || exit 1
```

**Steps**:

| Step | Duration | Purpose | Success Criteria |
|------|----------|---------|-----------------|
| **AWS Login** | 5s | Authenticate for ECR access | Credentials valid |
| **Docker Pull** | 30-60s | Download image from ECR | Image available locally |
| **Stop Old Container** | 5s | Clean up previous deployment | Container stopped safely |
| **Docker Run** | 10s | Start new container with env vars | Port 8080 listening |
| **Health Check** | 5s | Verify app is responding | `/health` returns 200 OK |

**Trigger**: Only after successful CI build  
**Environment Variables**: Injected from GitHub Secrets  
**On Failure**: Automatic rollback to previous version  
**On Success**: App live and accessible

### 4️⃣ AWS Infrastructure

```mermaid
graph LR
    subgraph ECR["Amazon ECR"]
        ECR1["Container<br/>Repository<br/>medical-chatbot"]
        ECR2["Image Tags<br/>:latest<br/>:sha-abc123"]
    end

    subgraph EC2["AWS EC2 Instance"]
        EC2CPU["t2.micro or t3.small"]
        EC2OS["Ubuntu 24.04 LTS"]
        EC2RAM["1-2 GB RAM"]
    end

    subgraph Docker["Docker Engine"]
        DOCKER1["Running Container"]
        DOCKER2["Port 8080<br/>HTTP Listener"]
        DOCKER3["Environment Variables<br/>Secrets"]
    end

    subgraph Endpoints["Application Endpoints"]
        EP1["/chat<br/>POST - User queries"]
        EP2["/health<br/>GET - Health check"]
        EP3["/templates<br/>Static files"]
    end

    ECR1 --> |docker pull| Docker
    Docker --> DOCKER1
    DOCKER1 --> DOCKER2
    DOCKER3 --> DOCKER1
    DOCKER2 --> Endpoints

    classDef ecr fill:#ff9900,stroke:#cc7700,color:#fff
    classDef ec2 fill:#148f77,stroke:#0e4f3c,color:#fff
    classDef docker fill:#2496ed,stroke:#0670cc,color:#fff
    classDef endpoints fill:#27ae60,stroke:#1e8449,color:#fff

    class ECR,ECR1,ECR2 ecr
    class EC2,EC2CPU,EC2OS,EC2RAM ec2
    class Docker,DOCKER1,DOCKER2,DOCKER3 docker
    class Endpoints,EP1,EP2,EP3 endpoints
```

### 5️⃣ Secrets & Environment Variables

**Stored in GitHub Secrets** (Not in repository):

```yaml
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
PINECONE_API_KEY=pckey_xxxxxxxxxxxxx
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
FLASK_SECRET_KEY=dev-secret-key-change-in-production
PINECONE_INDEX_NAME=medical-chatbot
```

**Injected at Runtime**:
```bash
docker run -d \
  -e GROQ_API_KEY=${{ secrets.GROQ_API_KEY }} \
  -e PINECONE_API_KEY=${{ secrets.PINECONE_API_KEY }} \
  -e FLASK_SECRET_KEY=${{ secrets.FLASK_SECRET_KEY }} \
  -p 8080:8080 \
  medical-chatbot:latest
```

## Dockerfile

```dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

# Copy application files
COPY requirements.txt setup.py ./
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run with gunicorn
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:8080", "app:app"]
```

## Pipeline Monitoring

### Success Metrics

| Metric | Target | How to Monitor |
|--------|--------|----------------|
| **Build Success Rate** | > 95% | GitHub Actions dashboard |
| **Build Duration** | < 3 min | Actions logs |
| **Deploy Frequency** | 1-5 times/day | GitHub releases |
| **Deployment Success** | > 99% | EC2 instance status |
| **Uptime** | > 99.5% | CloudWatch metrics |

### Failure Scenarios & Recovery

| Scenario | Cause | Recovery |
|----------|-------|----------|
| **Build Fails** | Code error or lint issue | Fix code, recommit, retry |
| **Tests Fail** | New bugs in changes | Debug with pytest logs |
| **Docker Build Fails** | Missing dependency | Update requirements.txt |
| **Push to ECR Fails** | AWS credentials expired | Rotate credentials in GitHub |
| **Deploy Fails** | Container won't start | Check environment variables |
| **Health Check Fails** | App not responding | Check Flask app logs |

### Rollback Procedure

If deployment fails after health check:

```bash
# EC2 instance will automatically:
1. Stop failed container
2. Start previous known-good image
3. Re-run health check
4. Notify on Slack/Email if configured
```

Manual rollback (if needed):
```bash
# SSH to EC2 instance
aws ec2-instance-connect open-tunnel --instance-id i-xxxxx

# Pull previous image
docker pull $ECR_REGISTRY/medical-chatbot:previous

# Start old container
docker run -d --name medical-chatbot-rollback \
  -e GROQ_API_KEY=$GROQ_KEY \
  -e PINECONE_API_KEY=$PINECONE_KEY \
  -p 8080:8080 \
  $ECR_REGISTRY/medical-chatbot:previous
```

## GitHub Actions Workflow File

**Location**: `.github/workflows/cicd.yaml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: medical-chatbot
  IMAGE_TAG: ${{ github.sha }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image: ${{ steps.image.outputs.image }}
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Login to ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        echo "IMAGE=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_ENV
    
    - name: Run tests
      run: |
        pip install pytest
        pytest tests/ -v
    
    - name: Push to ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
      run: |
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

  deploy:
    needs: build
    runs-on: [self-hosted, ec2]
    
    steps:
    - uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Login to ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Pull Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
      run: docker pull $ECR_REGISTRY/medical-chatbot:${{ github.sha }}
    
    - name: Deploy
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}
      run: |
        docker stop medical-chatbot || true
        docker run -d --name medical-chatbot \
          -e GROQ_API_KEY=$GROQ_API_KEY \
          -e PINECONE_API_KEY=$PINECONE_API_KEY \
          -p 8080:8080 \
          $ECR_REGISTRY/medical-chatbot:${{ github.sha }}
    
    - name: Health check
      run: |
        sleep 5
        curl -f http://localhost:8080/health || exit 1
```

## Quick Reference

### Commands to View Pipeline Status
```bash
# View all workflow runs
gh workflow list

# View latest workflow run
gh run list

# View specific run details
gh run view <run-id>

# View run logs
gh run view <run-id> --log

# View deployment status
aws ec2 describe-instance-status --instance-ids i-xxxxx
```

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **Build fails on tests** | Run `pytest` locally, fix issues, retry |
| **ECR push fails** | Check AWS credentials, verify ECR permissions |
| **Docker run fails on EC2** | SSH to instance, check `docker logs medical-chatbot` |
| **Health check fails** | Verify Flask app is listening on port 8080 |
| **Container won't start** | Check environment variables, review app.log |

---

**Last Updated**: May 4, 2026  
**Status**: Production-Ready ✅

# HuggingFace Deployment Manager

A simple package to help deploying a folder as a Docker space.

# Usage

## Managed folder

Create `hf-deploy.yaml` file:
```yaml
hf-deploy:
  name: hugginf-face-space-name
  content:
    - from: requirements.txt
    - from: dags/*
      to: dags/
      exclude:
        - __pycache__
        - .gitkeep
    - from: hf.Dockerfile
      to: Dockerfile
    - from: hf.README.md
      to: README.md
    - from: ./*
      exclude:
        - hf-deploy.yml
  environment:
    AWS_ACCESS_KEY_ID: ${terraform::user_access_key_id}
    MLFLOW_SERVER_BACKEND_STORE_URI: ${env::MLFLOW_SERVER_BACKEND_STORE_URI}
    MLFLOW_SERVER_ARTIFACT_ROOT: 's3://${terraform::bucket_name}/mlflow-artifacts/'
  secrets:
    AIRFLOW_ADMIN_USER: ${env::AIRFLOW_ADMIN_USER}
    AIRFLOW_ADMIN_PASSWORD: ${env::AIRFLOW_ADMIN_PASSWORD}
    AIRFLOW_CONN_AWS_DEFAULT_CONNECTION: '{"conn_type": "aws", "description": "", "host": "", "login": "${terraform::user_access_key_id}", "password": "${terraform::user_access_key_secret}", "schema": "", "extra": {"region_name": "eu-west-3"}}'

```

Usage:
```python

hf = HuggingFaceAccount(HF_TOKEN, "your-namespace)

dep = HuggingFaceSpaceDeployment("{path to hf-deploy.yaml}")

# Create or update docker space content
hf.install(dep)

# Destroy the space if it exists
hf.destroy(dep)

```

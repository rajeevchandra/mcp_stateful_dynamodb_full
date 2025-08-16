# Stateful MCP Server (Python) on ECS + DynamoDB

A minimal **stateful** MCP server that keeps session memory and a simple tool cache using **DynamoDB**, packaged as a Docker image and deployable to **ECS Fargate** with **Terraform**.

## Why stateful?
- Multi-turn workflows with memory
- Cache repeated tool results for speed
- Survives restarts (DynamoDB persistence)

- <img width="3840" height="1584" alt="Untitled diagram _ Mermaid Chart-2025-08-16-142540" src="https://github.com/user-attachments/assets/e8631109-6dac-4262-9a3a-b0193bcd1b97" />


<img width="3840" height="2714" alt="Untitled diagram _ Mermaid Chart-2025-08-16-142345" src="https://github.com/user-attachments/assets/fdf7ad71-a482-4dd0-ad8b-da181a44a9f1" />

<img width="3840" height="2630" alt="Untitled diagram _ Mermaid Chart-2025-08-16-142502" src="https://github.com/user-attachments/assets/edc16f7d-0731-4789-9486-d8a1e103306e" />



## Tools
- `add_note(session_id, note)` – append a note
- `get_notes(session_id)` – read notes
- `reset_session(session_id)` – delete notes for that session
- `echo_cached(text)` – uppercase w/ cache

## Quickstart (Windows, local)
```bat
cd app
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

aws dynamodb create-table --table-name mcp_state --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE --billing-mode PAY_PER_REQUEST
aws dynamodb update-time-to-live --table-name mcp_state --time-to-live-specification "Enabled=true, AttributeName=expiresAt"

set MCP_STATE_BACKEND=DYNAMODB
set MCP_STATE_TABLE=mcp_state
set AWS_REGION=us-east-1

python src\server_http.py --host 127.0.0.1 --port 3333


In another terminal:

cd app && .venv\Scripts\activate
python test_client.py


----- This is for local testing ------------

how to deploy to AWS using Terraform

Build & push image to ECR:

cd app
docker build -t mcp-dynamodb:latest .
set REGION=us-east-1
set REPO=mcp-dynamodb
aws ecr create-repository --repository-name %REPO% --region %REGION%
for /f %A in ('aws sts get-caller-identity --query Account --output text') do set ACCOUNT_ID=%A
set ECR_URI=%ACCOUNT_ID%.dkr.ecr.%REGION%.amazonaws.com/%REPO%:latest
aws ecr get-login-password --region %REGION% | docker login --username AWS --password-stdin %ACCOUNT_ID%.dkr.ecr.%REGION%.amazonaws.com
docker tag mcp-dynamodb:latest %ECR_URI%
docker push %ECR_URI%


cd ..\infra\terraform
(
echo region = "us-east-1"
echo project_name = "mcp-stateful"
echo container_image = "%ECR_URI%"
echo allowed_cidr = "YOUR.PUBLIC.IP/32"
) > terraform.tfvars

terraform init
terraform apply -auto-approve

Get public IP:

for /f %A in ('terraform output -raw cluster_name') do set CLUSTER=%A
for /f %A in ('terraform output -raw service_name') do set SERVICE=%A
for /f %A in ('aws ecs list-tasks --cluster %CLUSTER% --service-name %SERVICE% --query "taskArns[0]" --output text') do set TASK_ARN=%A
aws ecs describe-tasks --cluster %CLUSTER% --tasks %TASK_ARN% --query "tasks[0].attachments[0].details[?name=='publicIPv4Address'].value" --output text

test

curl http://<PUBLIC_IP>:3333/mcp/list_tools


destroy

terraform destroy -auto-approve

Costs

Fargate (0.25 vCPU/0.5GB) + public IP + DynamoDB on-demand ≈ a few cents/hour for tests. Destroy to stop charges.

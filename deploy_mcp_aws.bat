@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ==== User-adjustable defaults ====
set "REGION=us-east-1"
set "REPO=mcp-dynamodb"
set "PROJECT_NAME=mcp-stateful"

REM ==== Expecting folders: app\ and infra\terraform\ under this folder ====
set "ROOT=%~dp0"
set "APP_DIR=%ROOT%app"
set "TERRAFORM_DIR=%ROOT%infra\terraform"

echo.
echo === Building and Deploying Stateful MCP Server to AWS (ECS Fargate + DynamoDB) ===
echo Region: %REGION%
echo Repo:   %REPO%
echo Project:%PROJECT_NAME%
echo Root:   %ROOT%
echo.

REM ---- Step 1: Build Docker image (from app/) ----
if not exist "%APP_DIR%\Dockerfile" (
  echo [ERROR] Could not find Dockerfile at "%APP_DIR%\Dockerfile"
  echo Make sure this .bat is in the project root next to app\ and infra\
  exit /b 1
)
pushd "%APP_DIR%"
echo [*] docker build -t %REPO%:latest .
docker build -t %REPO%:latest . || (echo [ERROR] Docker build failed & popd & exit /b 1)
popd

REM ---- Step 2: Ensure ECR repo exists and push image ----
echo [*] Creating ECR repository (ok if it already exists)...
aws ecr create-repository --repository-name %REPO% --region %REGION% 1>nul 2>nul

for /f %%A in ('aws sts get-caller-identity --query Account --output text') do set "ACCOUNT_ID=%%A"
if "%ACCOUNT_ID%"=="" (
  echo [ERROR] Could not fetch AWS Account ID. Is AWS CLI configured? (aws configure)
  exit /b 1
)

set "ECR_REG=%ACCOUNT_ID%.dkr.ecr.%REGION%.amazonaws.com"
set "ECR_URI=%ECR_REG%/%REPO%:latest"
echo [*] Logging in to ECR: %ECR_REG%
aws ecr get-login-password --region %REGION% | docker login --username AWS --password-stdin %ECR_REG% || (echo [ERROR] ECR login failed & exit /b 1)

echo [*] Tagging & pushing: %ECR_URI%
docker tag %REPO%:latest %ECR_URI% || (echo [ERROR] Docker tag failed & exit /b 1)
docker push %ECR_URI% || (echo [ERROR] Docker push failed & exit /b 1)

REM ---- Step 3: Prepare terraform.tfvars ----
if not exist "%TERRAFORM_DIR%" (
  echo [ERROR] Terraform folder not found at "%TERRAFORM_DIR%"
  exit /b 1
)

REM Auto-detect your public IP with curl (if available); else open to 0.0.0.0/0
set "ALLOWED_CIDR="
for /f %%A in ('curl -s ifconfig.me 2^>nul') do set "ALLOWED_CIDR=%%A/32"
if "%ALLOWED_CIDR%"=="/32" set "ALLOWED_CIDR=0.0.0.0/0"

echo [*] Writing terraform.tfvars (allowed_cidr=%ALLOWED_CIDR%)
(
  echo region         = "%REGION%"
  echo project_name   = "%PROJECT_NAME%"
  echo container_image = "%ECR_URI%"
  echo allowed_cidr   = "%ALLOWED_CIDR%"
)> "%TERRAFORM_DIR%\terraform.tfvars"

REM ---- Step 4: Terraform init/apply ----
pushd "%TERRAFORM_DIR%"
echo [*] terraform init
terraform init || (echo [ERROR] terraform init failed & popd & exit /b 1)

echo [*] terraform apply -auto-approve
terraform apply -auto-approve || (echo [ERROR] terraform apply failed & popd & exit /b 1)

REM ---- Step 5: Fetch Public IP for the running task ----
for /f %%A in ('terraform output -raw cluster_name') do set "CLUSTER=%%A"
for /f %%A in ('terraform output -raw service_name') do set "SERVICE=%%A"

for /f %%A in ('aws ecs list-tasks --cluster "!CLUSTER!" --service-name "!SERVICE!" --query "taskArns[0]" --output text') do set "TASK_ARN=%%A"

for /f %%A in ('aws ecs describe-tasks --cluster "!CLUSTER!" --tasks "!TASK_ARN!" --query "tasks[0].attachments[0].details[?name=='publicIPv4Address'].value^|[0]" --output text') do set "PUBLIC_IP=%%A"

if "%PUBLIC_IP%"=="" (
  for /f %%A in ('aws ecs describe-tasks --cluster "!CLUSTER!" --tasks "!TASK_ARN!" --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value^|[0]" --output text') do set "ENI=%%A"
  for /f %%A in ('aws ec2 describe-network-interfaces --network-interface-ids "!ENI!" --query "NetworkInterfaces[0].Association.PublicIp" --output text') do set "PUBLIC_IP=%%A"
)

echo.
echo ================= DEPLOY COMPLETE =================
echo Public IP: %PUBLIC_IP%
echo MCP list tools: http://%PUBLIC_IP%:3333/mcp/list_tools
echo Add note:       curl -X POST -H "Content-Type: application/json" -d "{\"name\":\"add_note\",\"arguments\":{\"session_id\":\"demo\",\"note\":\"hello from ECS\"}}" http://%PUBLIC_IP%:3333/mcp/call_tool
echo ==================================================
popd

endlocal

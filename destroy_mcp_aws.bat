@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ==== Must match your deploy ====
set "REGION=us-east-1"
set "REPO=mcp-dynamodb"
set "PROJECT_NAME=mcp-stateful"

set "ROOT=%~dp0"
set "TERRAFORM_DIR=%ROOT%infra\terraform"

echo.
echo === Destroying Stateful MCP Server resources (Terraform + AWS cleanup) ===
echo Region: %REGION%
echo Repo:   %REPO%
echo Project:%PROJECT_NAME%
echo.

REM ---- Step 1: Terraform destroy (removes VPC, ECS, IAM, DynamoDB, Logs if TF created them)
if exist "%TERRAFORM_DIR%" (
  pushd "%TERRAFORM_DIR%"
  echo [*] terraform destroy -auto-approve
  terraform destroy -auto-approve
  popd
) else (
  echo [!] Terraform folder not found at "%TERRAFORM_DIR%". Skipping TF destroy.
)

REM ---- Step 2: Explicitly delete DynamoDB table (safe if already gone)
echo [*] Deleting DynamoDB table mcp_state (ok if it was already deleted)...
aws dynamodb delete-table --table-name mcp_state --region %REGION% 1>nul 2>nul

REM ---- Step 3: ECR cleanup (delete all images, then the repo)
echo [*] Cleaning up ECR repository: %REPO% (region %REGION%)
set "TMPJSON=%TEMP%\ecr_images_%RANDOM%.json"
aws ecr list-images --repository-name %REPO% --region %REGION% --query "imageIds[*]" --output json > "%TMPJSON%" 2>nul
aws ecr batch-delete-image --repository-name %REPO% --region %REGION% --image-ids file://%TMPJSON% 1>nul 2>nul
del /f /q "%TMPJSON%" 2>nul
aws ecr delete-repository --repository-name %REPO% --force --region %REGION% 1>nul 2>nul

REM ---- Step 4: Extra safety cleanup for logs and ECS (ignore errors if not found)
echo [*] Cleaning CloudWatch log group and ECS leftovers...
aws logs delete-log-group --log-group-name "/ecs/%PROJECT_NAME%" --region %REGION% 1>nul 2>nul

set "CLUSTER=%PROJECT_NAME%-cluster"
set "SERVICE=%PROJECT_NAME%-svc"
aws ecs update-service --cluster %CLUSTER% --service %SERVICE% --desired-count 0 --region %REGION% 1>nul 2>nul
aws ecs delete-service  --cluster %CLUSTER% --service %SERVICE% --force --region %REGION% 1>nul 2>nul
aws ecs delete-cluster  --cluster %CLUSTER% --region %REGION% 1>nul 2>nul

REM Optional: deregister any leftover task definitions for this family
for /f %%A in ('aws ecs list-task-definitions --family-prefix %PROJECT_NAME%-task --region %REGION% --query "taskDefinitionArns[]" --output text') do (
  aws ecs deregister-task-definition --task-definition %%A --region %REGION% 1>nul 2>nul
)

echo.
echo ============ CLEANUP COMPLETE ============
echo Verified nothing left? Run:
echo   aws dynamodb list-tables --region %REGION%
echo   aws ecr describe-repositories --region %REGION%
echo   aws ecs list-clusters --region %REGION%
echo   aws logs describe-log-groups --log-group-name-prefix /ecs/ --region %REGION%
echo =========================================
endlocal

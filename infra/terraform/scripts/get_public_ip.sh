
#!/usr/bin/env bash
set -euo pipefail

CLUSTER="$1"
SERVICE="$2"

TASK_ARN=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name "$SERVICE" --query 'taskArns[0]' --output text)
if [ "$TASK_ARN" = "None" ]; then
  echo "No running tasks found."
  exit 1
fi

aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK_ARN" \
  --query 'tasks[0].attachments[0].details[?name==`publicIPv4Address`].value' --output text

#!/usr/bin/env bash
# Deploy NexusDesk without the SAM CLI: build an arm64 Lambda package, upload it,
# then let CloudFormation expand the AWS::Serverless transform server side.
#
#   aws login                     # or: aws configure
#   export AWS_REGION=us-east-1
#   export JWT_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
#   export OPENROUTER_API_KEY=...            # optional
#   export CORS_ORIGINS=https://your-frontend
#   bash infra/deploy.sh
set -euo pipefail

STACK=${STACK:-nexusdesk}
REGION=${AWS_REGION:-us-east-1}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BUILD="$ROOT/.aws-sam/build"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ARTIFACTS="${ARTIFACT_BUCKET:-$STACK-artifacts-$ACCOUNT}"

: "${JWT_SECRET:?set JWT_SECRET to a generated secret}"

echo "==> Building arm64 package"
rm -rf "$BUILD" && mkdir -p "$BUILD"
cp -r "$ROOT/backend/app" "$BUILD/app"
find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} +
python -m pip install \
  --quiet --target "$BUILD" \
  --platform manylinux2014_aarch64 --python-version 3.12 \
  --implementation cp --only-binary=:all: --upgrade \
  boto3 fastapi langgraph mangum openai "passlib[bcrypt]" "bcrypt<4.1" \
  email-validator pydantic-settings pypdf "python-jose[cryptography]" python-multipart

# Trim what Lambda never needs; the unzipped package must stay under 250 MB.
find "$BUILD" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$BUILD" -name '*.pyc' -delete
find "$BUILD" -type d \( -name 'tests' -o -name 'test' -o -name '*.dist-info' \) -prune -exec rm -rf {} +
echo "    unzipped: $(du -sh "$BUILD" | cut -f1)"

rm -f "$ROOT/.aws-sam/api.zip"
(cd "$BUILD" && zip -qr "$ROOT/.aws-sam/api.zip" .)

echo "==> Ensuring artifact bucket $ARTIFACTS"
aws s3api head-bucket --bucket "$ARTIFACTS" 2>/dev/null || \
  aws s3 mb "s3://$ARTIFACTS" --region "$REGION" >/dev/null
aws s3 cp "$ROOT/.aws-sam/api.zip" "s3://$ARTIFACTS/api.zip" --region "$REGION" >/dev/null

echo "==> Deploying stack $STACK"
python - "$ROOT/infra/template.yaml" "$ROOT/.aws-sam/packaged.yaml" "$ARTIFACTS" <<'PY'
import sys
source, target, bucket = sys.argv[1:4]
text = open(source, encoding="utf-8").read()
text = text.replace(
    "      CodeUri: ../backend\n",
    f"      CodeUri:\n        Bucket: {bucket}\n        Key: api.zip\n",
)
open(target, "w", encoding="utf-8").write(text)
PY

aws cloudformation deploy \
  --template-file "$ROOT/.aws-sam/packaged.yaml" \
  --stack-name "$STACK" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "JwtSecret=$JWT_SECRET" \
    "OpenRouterApiKey=${OPENROUTER_API_KEY:-}" \
    "CorsOrigins=${CORS_ORIGINS:-http://localhost:3000}"

URL=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" --output text)
echo "==> API: $URL"
echo "==> Health: $(curl -s "${URL}health")"
echo "==> Set NEXT_PUBLIC_API_URL=${URL}api/v1"

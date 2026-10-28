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

if [ -n "${SKIP_BUILD:-}" ] && [ -f "$ROOT/.aws-sam/api.zip" ]; then
  echo "==> Reusing existing package (SKIP_BUILD set)"
else
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
# Keep *.dist-info: pydantic resolves email-validator through package metadata at import.
find "$BUILD" -type d \( -name 'tests' -o -name 'test' \) -prune -exec rm -rf {} +
echo "    unzipped: $(du -sh "$BUILD" | cut -f1)"

rm -f "$ROOT/.aws-sam/api.zip"
python - "$BUILD" "$ROOT/.aws-sam/api.zip" <<'PY'
import pathlib
import sys
import zipfile

source, target = (pathlib.Path(value) for value in sys.argv[1:3])
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(source.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(source).as_posix())
print(f"    zipped: {target.stat().st_size // (1024 * 1024)} MB")
PY
fi

echo "==> Ensuring artifact bucket $ARTIFACTS"
aws s3api head-bucket --bucket "$ARTIFACTS" 2>/dev/null || \
  aws s3 mb "s3://$ARTIFACTS" --region "$REGION" >/dev/null
# Content-addressed key: an unchanged key would leave CloudFormation with nothing to update.
KEY="api-$(python -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()[:12])' "$ROOT/.aws-sam/api.zip").zip"
aws s3 cp "$ROOT/.aws-sam/api.zip" "s3://$ARTIFACTS/$KEY" --region "$REGION" >/dev/null
echo "    key: $KEY"

echo "==> Deploying stack $STACK"
python - "$ROOT/infra/template.yaml" "$ROOT/.aws-sam/packaged.yaml" "$ARTIFACTS" "$KEY" <<'PY'
import sys
source, target, bucket, key = sys.argv[1:5]
text = open(source, encoding="utf-8").read()
text = text.replace(
    "      CodeUri: ../backend\n",
    f"      CodeUri:\n        Bucket: {bucket}\n        Key: {key}\n",
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
    "CorsOrigins=${CORS_ORIGINS:-http://localhost:3000}" \
    "ExecutionRoleArn=${EXECUTION_ROLE_ARN:-}"

URL=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" --output text)
echo "==> API: $URL"
echo "==> Health: $(curl -s "${URL}health")"
echo "==> Set NEXT_PUBLIC_API_URL=${URL}api/v1"

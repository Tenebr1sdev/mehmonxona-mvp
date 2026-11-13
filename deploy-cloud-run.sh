#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION}"
: "${INSTANCE_CONNECTION_NAME:?Set INSTANCE_CONNECTION_NAME as project:region:instance}"
: "${DATABASE_SECRET:?Set DATABASE_SECRET to Secret Manager secret name for the SQLAlchemy URL}"
: "${JWT_SECRET:?Set JWT_SECRET to Secret Manager secret name for the JWT key}"
: "${ADMIN_SECRET:?Set ADMIN_SECRET to Secret Manager secret name for the admin password}"
: "${DEMO_SECRET:?Set DEMO_SECRET to Secret Manager secret name for demo user passwords}"
: "${GCS_BUCKET:?Set GCS_BUCKET for persistent file uploads}"
SERVICE_NAME="${SERVICE_NAME:-hotel-management-mvp}"
gcloud config set project "$PROJECT_ID"
gcloud builds submit --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/hotel/${SERVICE_NAME}:latest" .
gcloud run deploy "$SERVICE_NAME" \
  --image "${REGION}-docker.pkg.dev/${PROJECT_ID}/hotel/${SERVICE_NAME}:latest" \
  --region "$REGION" --platform managed --allow-unauthenticated \
  --add-cloudsql-instances "$INSTANCE_CONNECTION_NAME" \
  --set-secrets "DATABASE_URL=${DATABASE_SECRET}:latest,SECRET_KEY=${JWT_SECRET}:latest,ADMIN_PASSWORD=${ADMIN_SECRET}:latest,DEMO_PASSWORD=${DEMO_SECRET}:latest" \
  --set-env-vars "UPLOAD_DIR=/tmp/hotel-uploads,GCS_BUCKET=${GCS_BUCKET},MAX_UPLOAD_MB=12" \
  --port 8000 --min 0 --max 3

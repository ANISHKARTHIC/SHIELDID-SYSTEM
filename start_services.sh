#!/bin/bash
set -e
# Local infra-only bootstrap for backend/ai-service dev without Docker
# Compose: Postgres+pgvector and Redis on the same ports backend/.env
# defaults to (5432/6379), so no .env edits are needed after running this.
# Storage is real S3 (see backend/.env's S3_* vars) — MinIO isn't part of
# the stack anymore, this script no longer starts one.

echo "Starting Postgres with pgvector..."
podman run -d --name pub_entry_db --replace \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=adminpassword \
  -e POSTGRES_DB=pub_entry_db \
  -p 5432:5432 \
  docker.io/pgvector/pgvector:pg16

echo "Starting Redis..."
podman run -d --name pub_entry_redis --replace \
  -p 6379:6379 \
  docker.io/library/redis:7-alpine

echo "All services started successfully!"
echo "Postgres: localhost:5432 | Redis: localhost:6379 (matches backend/.env defaults)"

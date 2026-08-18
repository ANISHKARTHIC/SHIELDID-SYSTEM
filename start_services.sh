#!/bin/bash
set -e

echo "Starting Postgres with pgvector..."
podman run -d --name pub_entry_db --replace \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=adminpassword \
  -e POSTGRES_DB=pub_entry_db \
  -p 5433:5432 \
  docker.io/pgvector/pgvector:pg16

echo "Starting Redis..."
podman run -d --name pub_entry_redis --replace \
  -p 6380:6379 \
  docker.io/library/redis:7-alpine

echo "Starting MinIO..."
podman run -d --name pub_entry_minio --replace \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 9000:9000 \
  -p 9001:9001 \
  docker.io/minio/minio:latest server /data --console-address ":9001"

echo "Waiting for MinIO to start..."
sleep 5

echo "Creating MinIO buckets..."
podman exec pub_entry_minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
podman exec pub_entry_minio mc mb myminio/verification-images --ignore-existing || true
podman exec pub_entry_minio mc anonymous set public myminio/verification-images || true

echo "All services started successfully!"

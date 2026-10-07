#!/bin/sh
set -eu

IMAGE="container-ghost"
CONTAINER="container-ghost-test"

cleanup() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "Building Container Ghost..."
docker build -t "$IMAGE" .

echo "Starting Container Ghost..."
docker run -d \
    --name "$CONTAINER" \
    -p 8080:8080 \
    -e APP_HOST=0.0.0.0 \
    -e APP_PORT=8080 \
    "$IMAGE"

echo "Waiting for the container..."
sleep 3

echo "Container status:"
docker ps --filter "name=$CONTAINER"

echo "Container health:"
docker inspect \
    --format '{{.State.Health.Status}}' \
    "$CONTAINER"

echo "Testing application..."
if curl -fsS http://localhost:8080/health >/dev/null; then
    echo "Health endpoint is working."
else
    echo "Health endpoint failed."
    exit 1
fi

echo "Container Ghost solution completed."

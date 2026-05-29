#!/bin/bash
# Build and optionally run Lilith Agent Docker image
set -e

IMAGE_NAME="lilith-agent"
TAG="${1:-latest}"

echo "Building Docker image: ${IMAGE_NAME}:${TAG}..."

cd "$(dirname "$0")/.."
docker build -t "${IMAGE_NAME}:${TAG}" .

echo ""
echo "Image built: ${IMAGE_NAME}:${TAG}"
echo "Size: $(docker image inspect "${IMAGE_NAME}:${TAG}" --format='{{.Size}}' | numfmt --to=iec)"
echo ""
echo "Run: docker run -it --rm -v ~/.lilith:/app/.lilith ${IMAGE_NAME}:${TAG}"
echo "Or:  docker run -it --rm ${IMAGE_NAME}:${TAG} --provider qwen3.7 -m 'hello'"

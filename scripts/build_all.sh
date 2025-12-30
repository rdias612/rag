#!/usr/bin/env bash
# Build all Dockerfiles recursively
# Usage: ./build_all.sh [--no-cache]
set -euo pipefail
NO_CACHE=0
if [[ ${1-} == "--no-cache" ]]; then NO_CACHE=1; fi

shopt -s globstar
IMAGE_TAG=latest

if [[ ${1-} == "--no-cache" ]]; then
  NO_CACHE=1
  IMAGE_TAG=${2-}
  if [ -z "$IMAGE_TAG" ]; then IMAGE_TAG=latest; fi
  files=(**/Dockerfile)
  repo=$(basename "$PWD")
  IMAGE_TAG=${1-}
  if [ -z "$IMAGE_TAG" ]; then IMAGE_TAG=latest; fi
fi
files=(**/Dockerfile)
if [ ${#files[@]} -eq 0 ]; then
  echo "Nenhum Dockerfile encontrado."
  exit 0
fi

for file in "${files[@]}"; do
  context=$(dirname "$file")
    # tag from relative path; use repo name when context is root
    if [ "$context" = "." ] || [ -z "$context" ]; then
      tag="$repo"
    else
      tag=$(echo "$context" | sed 's:^\./::; s:/:-:g; s:[/ ]:-:g')
    fi
    # sanitize: remove leading dots or dashes
    tag=$(echo "$tag" | sed 's/^[.-]\+//; s/[[:space:]]//g')
    if [ -z "$tag" ]; then tag=image; fi
  fulltag="$tag:$IMAGE_TAG"
  echo "\nBuilding: $file (context: $context) -> tag: $fulltag"
  if [ $NO_CACHE -eq 1 ]; then
    docker build --no-cache -t "$fulltag" -f "$file" "$context"
  else
    docker build -t "$fulltag" -f "$file" "$context"
  fi
done

echo "\nBuilds completos."

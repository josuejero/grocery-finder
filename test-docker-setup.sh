#!/bin/bash

echo "1. Checking existing volumes..."
docker volume ls | grep grocery_finder

echo "2. Checking volume usage..."
docker system df -v | grep grocery_finder

echo "3. Checking container storage..."
for container in $(docker ps --format '{{.Names}}' | grep grocery_finder); do
    echo "Container: $container"
    docker container inspect $container | grep -A 5 "Mounts"
done

echo "4. Checking container logs size..."
for container in $(docker ps --format '{{.Names}}' | grep grocery_finder); do
    echo "Log size for $container:"
    ls -lh $(docker inspect --format='{{.LogPath}}' $container)
done

echo "5. Checking directory permissions..."
services_dirs=(
    "./services/api_gateway"
    "./services/auth_service"
    "./services/user_service"
    "./services/price_service"
)

for dir in "${services_dirs[@]}"; do
    echo "Checking $dir:"
    ls -ld "$dir"
done

echo "6. Checking container health..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep grocery_finder
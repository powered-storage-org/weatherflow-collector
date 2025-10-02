#!/bin/bash

# WeatherFlow Collector Docker Build Script

set -e

echo "🌤️  WeatherFlow Collector Docker Build Script"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running"
    exit 1
fi

print_success "Docker is available and running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_warning "docker-compose is not available, using 'docker compose' instead"
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

# Build options
DOCKERFILE="Dockerfile"
IMAGE_NAME="weatherflow-collector"
TAG="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --optimized)
            DOCKERFILE="Dockerfile.optimized"
            print_status "Using optimized Dockerfile"
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --optimized    Use the optimized multi-stage Dockerfile"
            echo "  --tag TAG      Set the image tag (default: latest)"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "Building WeatherFlow Collector image..."
print_status "Dockerfile: $DOCKERFILE"
print_status "Image: $IMAGE_NAME:$TAG"

# Build the image
if [ "$DOCKERFILE" = "Dockerfile.optimized" ]; then
    docker build -f $DOCKERFILE -t $IMAGE_NAME:$TAG .
else
    $DOCKER_COMPOSE_CMD build weatherflow-collector
fi

if [ $? -eq 0 ]; then
    print_success "WeatherFlow Collector image built successfully!"
    echo ""
    print_status "Available commands:"
    echo "  🚀 Start the stack:     $DOCKER_COMPOSE_CMD up -d"
    echo "  📊 View logs:           $DOCKER_COMPOSE_CMD logs -f weatherflow-collector"
    echo "  🛑 Stop the stack:      $DOCKER_COMPOSE_CMD down"
    echo "  🔄 Restart collector:   $DOCKER_COMPOSE_CMD restart weatherflow-collector"
    echo "  🧹 Clean up:            $DOCKER_COMPOSE_CMD down -v"
    echo ""
    print_status "Image details:"
    docker images | grep $IMAGE_NAME
else
    print_error "Failed to build WeatherFlow Collector image"
    exit 1
fi

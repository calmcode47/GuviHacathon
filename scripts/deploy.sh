#!/bin/bash
# Deployment script for AI Voice Detection API

set -e

echo "🚀 Starting deployment..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker build -t voice-detector:latest .

# Check if API_KEY is set
if [ -z "$API_KEY" ]; then
    echo "⚠️  Warning: API_KEY not set, using default test key"
    export API_KEY=sk_test_123456789
fi

# Run container
echo "🐳 Starting container..."
docker run -d \
    --name voice-detector \
    -p 8000:8000 \
    -e API_KEY="$API_KEY" \
    --restart unless-stopped \
    voice-detector:latest

echo "✅ Deployment complete!"
echo "🌐 API available at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo "🎨 Demo interface at http://localhost:8000/"

# Wait a moment and check health
sleep 2
echo ""
echo "🏥 Checking health endpoint..."
curl -s http://localhost:8000/health | python3 -m json.tool || echo "Health check failed"

echo ""
echo "To stop the container: docker stop voice-detector"
echo "To remove the container: docker rm voice-detector"

#!/bin/bash

###############################################################################
# Sports Card Tagger - Automated Docker Setup Script for Linux
# Run this script on a fresh Linux server to set up everything automatically
###############################################################################

set -e  # Exit on error

echo "🚀 Sports Card Tagger - Docker Setup Script"
echo "=============================================="
echo ""

# Check if running on Linux
if [[ ! "$OSTYPE" == "linux"* ]]; then
    echo "❌ This script only works on Linux. Please run on Ubuntu/Debian."
    exit 1
fi

# Check if running with proper permissions
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use: sudo bash setup-docker.sh)"
   exit 1
fi

echo "📦 Step 1: Installing Docker & Docker Compose..."
apt-get update
apt-get install -y docker.io docker-compose git curl wget

echo "✅ Docker installed"
echo ""

echo "👤 Step 2: Setting up Docker group..."
usermod -aG docker ${SUDO_USER}
newgrp docker

echo "✅ Docker group configured"
echo ""

echo "📂 Step 3: Cloning repository to /opt/sports-card-tagger..."
cd /opt
if [ -d "sports-card-tagger" ]; then
    echo "   (Directory exists, pulling latest changes)"
    cd sports-card-tagger
    git pull origin main
else
    git clone https://github.com/yourusername/sports-card-tagger.git
    cd sports-card-tagger
fi

echo "✅ Repository ready"
echo ""

echo "🔐 Step 4: Setting up environment..."
if [ ! -f ".env" ]; then
    echo "   Creating .env file from template..."
    cp .env.example .env
    
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your credentials:"
    echo "   nano /opt/sports-card-tagger/.env"
    echo ""
    echo "   Required variables:"
    echo "   - POSTGRES_PASSWORD (set a strong password)"
    echo "   - OPENAI_API_KEY"
    echo ""
    echo "   Press ENTER after you've saved the file..."
    read
else
    echo "   .env already exists (skipping)"
fi

echo "✅ Environment configured"
echo ""

echo "🏗️  Step 5: Building Docker images..."
docker-compose build

echo "✅ Images built"
echo ""

echo "🚀 Step 6: Starting containers..."
docker-compose up -d

echo "✅ Containers started"
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL failed to start"
        exit 1
    fi
    sleep 1
done

sleep 5

# Check API
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null; then
        echo "✅ API is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠️  API still starting (this is normal)"
    fi
    sleep 1
done

echo ""
echo "=============================================="
echo "✅ SETUP COMPLETE!"
echo "=============================================="
echo ""

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo "📊 Service Status:"
docker-compose ps
echo ""

echo "🌐 Access Points:"
echo "   • API: http://${SERVER_IP}:8000"
echo "   • Swagger Docs: http://${SERVER_IP}:8000/docs"
echo "   • ReDoc: http://${SERVER_IP}:8000/redoc"
echo ""

echo "📝 Useful Commands:"
echo "   • View logs: docker-compose logs -f app"
echo "   • Restart: docker-compose restart"
echo "   • Stop: docker-compose stop"
echo "   • Start: docker-compose up -d"
echo ""

echo "📚 Documentation:"
echo "   • Full guide: /opt/sports-card-tagger/DOCKER-DEPLOYMENT.md"
echo "   • README: /opt/sports-card-tagger/README.md"
echo ""

echo "🎯 Next Steps:"
echo "   1. Share http://${SERVER_IP}:8000 with your team"
echo "   2. Test with: curl http://${SERVER_IP}:8000"
echo "   3. View API docs: http://${SERVER_IP}:8000/docs"
echo ""

echo "💾 Backup Database:"
echo "   docker-compose exec postgres pg_dump -U postgres CollectorInvestor > backup.sql"
echo ""

echo "❓ Need help?"
echo "   Check DOCKER-DEPLOYMENT.md for common issues and troubleshooting"
echo ""

#!/bin/bash
# deploy-free-tier.sh
# One-script deployment to Vercel + Railway + Supabase (all free)

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    ActionRAG Free Tier Deployment Script                   ║"
echo "║    Deploy to Vercel (frontend) + Railway (backend)         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check dependencies
check_dependencies() {
  echo "${YELLOW}[1/6] Checking dependencies...${NC}"

  if ! command -v node &> /dev/null; then
    echo "${RED}Error: Node.js not found. Install from https://nodejs.org${NC}"
    exit 1
  fi

  if ! command -v npm &> /dev/null; then
    echo "${RED}Error: npm not found.${NC}"
    exit 1
  fi

  # Check for Vercel CLI (optional, can install)
  if ! command -v vercel &> /dev/null; then
    echo "${YELLOW}Installing Vercel CLI...${NC}"
    npm install -g vercel
  fi

  # Check for Railway CLI (optional)
  if ! command -v railway &> /dev/null; then
    echo "${YELLOW}Installing Railway CLI...${NC}"
    npm install -g @railway/cli
  fi

  echo "${GREEN}✓ Dependencies OK${NC}"
}

# Setup environment
setup_env() {
  echo "${YELLOW}[2/6] Setting up environment...${NC}"

  if [ ! -f .env ]; then
    echo "${RED}Error: .env file not found. Copy .env.template to .env first${NC}"
    echo "  cp .env.template .env"
    echo "  # Then edit .env with your API keys"
    exit 1
  fi

  echo "${GREEN}✓ .env file found${NC}"
}

# Deploy frontend to Vercel
deploy_frontend() {
  echo "${YELLOW}[3/6] Deploying frontend to Vercel...${NC}"

  cd frontend

  # Install dependencies
  npm install

  # Deploy
  vercel --prod

  # Get deployment URL
  VERCEL_URL=$(vercel inspect --prod 2>/dev/null | grep "https://" | head -1)
  echo "${GREEN}✓ Frontend deployed to: $VERCEL_URL${NC}"

  cd ..
}

# Deploy backend to Railway
deploy_backend() {
  echo "${YELLOW}[4/6] Deploying backend to Railway...${NC}"

  cd backend

  # Create requirements.txt if not exists
  if [ ! -f requirements.txt ]; then
    echo "${RED}Error: requirements.txt not found${NC}"
    exit 1
  fi

  # Initialize Railway
  if [ ! -f railway.json ]; then
    railway init
  fi

  # Deploy
  railway up

  # Get backend URL
  echo ""
  echo "${YELLOW}After deployment, get your Railway URL${NC}"
  echo "  railway env && railway status"
  echo ""

  cd ..
}

# Verify Supabase
verify_supabase() {
  echo "${YELLOW}[5/6] Verifying Supabase setup...${NC}"

  if [ -z "$SUPABASE_URL" ]; then
    echo "${RED}Error: SUPABASE_URL not set in .env${NC}"
    exit 1
  fi

  if [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "${RED}Error: SUPABASE_SERVICE_KEY not set in .env${NC}"
    exit 1
  fi

  curl -s "$SUPABASE_URL/rest/v1/" -H "apikey: $SUPABASE_SERVICE_KEY" > /dev/null

  if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Supabase connection verified${NC}"
  else
    echo "${RED}Error: Cannot connect to Supabase${NC}"
    exit 1
  fi
}

# Final checklist
final_checklist() {
  echo "${YELLOW}[6/6] Final checklist...${NC}"

  echo ""
  echo "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo "${GREEN}║        DEPLOYMENT COMPLETE!                               ║${NC}"
  echo "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "Next steps:"
  echo ""
  echo "1. ${YELLOW}Get your Railway backend URL:${NC}"
  echo "   railway env && railway status"
  echo ""
  echo "2. ${YELLOW}Set NEXT_PUBLIC_API_URL in Vercel environment:${NC}"
  echo "   vercel env add NEXT_PUBLIC_API_URL https://your-railway-url"
  echo "   vercel redeploy"
  echo ""
  echo "3. ${YELLOW}Keep backend warm (prevents sleep after 30 min):${NC}"
  echo "   Add a cron job at EasyCron.com"
  echo "   URL: https://your-railway-url/api/v1/chat/health"
  echo "   Interval: Every 15 minutes"
  echo ""
  echo "4. ${YELLOW}Monitor performance:${NC}"
  echo "   Vercel: vercel logs"
  echo "   Railway: railway logs"
  echo ""
  echo "📊 Expected Response Times:"
  echo "   - Fast endpoint (/fast): 2-4 seconds"
  echo "   - Streaming endpoint (/stream): 1-2s to first token"
  echo ""
  echo "💰 Monthly Cost (Free Tier):"
  echo "   Vercel: $0"
  echo "   Railway: $0 (500 hours free)"
  echo "   Supabase: $0 (500MB storage)"
  echo "   Groq: $0 (free tier)"
  echo "   ---"
  echo "   TOTAL: $0 /month 🎉"
  echo ""
}

# Main execution
main() {
  check_dependencies
  setup_env

  # Ask which components to deploy
  echo ""
  echo "Choose what to deploy:"
  echo "1) Frontend only (Vercel)"
  echo "2) Backend only (Railway)"
  echo "3) Both (frontend + backend) – this takes longer"
  echo "4) Just verify Supabase"
  echo ""
  read -p "Enter choice (1-4): " choice

  case $choice in
    1)
      deploy_frontend
      ;;
    2)
      deploy_backend
      ;;
    3)
      deploy_frontend
      deploy_backend
      ;;
    4)
      verify_supabase
      ;;
    *)
      echo "Invalid choice"
      exit 1
      ;;
  esac

  final_checklist
}

main "$@"

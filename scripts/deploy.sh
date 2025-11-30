#!/bin/bash
# 🚀 Trading Bots VPS Deployment Script
# This script ensures clean deployment on any VPS

set -e  # Exit on any error

echo "🚀 Starting Trading Bots VPS Deployment..."
echo "============================================="

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

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found. Please run this script from the trading-bots directory."
    exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.13 if not present
print_status "Checking Python installation..."
if ! command -v python3.13 &> /dev/null; then
    print_status "Installing Python 3.13..."
    sudo apt install software-properties-common -y
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install python3.13 python3.13-venv python3.13-dev -y
else
    print_success "Python 3.13 already installed"
fi

# Verify Python version
PYTHON_VERSION=$(python3.13 --version 2>&1 | grep -oP 'Python \K[0-9]+\.[0-9]+')
if [[ $PYTHON_VERSION != "3.13" ]]; then
    print_warning "Python 3.13 not found, using available python3"
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python3.13"
fi

# Clean any existing virtual environment
print_status "Setting up clean virtual environment..."
if [ -d "venv" ]; then
    print_warning "Removing existing venv directory..."
    rm -rf venv
fi

# Create fresh virtual environment
$PYTHON_CMD -m venv venv
print_success "Virtual environment created"

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
pip install --upgrade pip

# Install requirements with error handling
print_status "Installing Python dependencies..."
if pip install -r requirements.txt; then
    print_success "Core dependencies installed"
else
    print_error "Failed to install core dependencies"
    exit 1
fi

# Install additional packages that might not be in requirements.txt
print_status "Installing additional packages..."
ADDITIONAL_PACKAGES=(
    "alpaca-trade-api"
    "python-dotenv"
    "schedule"
    "loguru"
)

for package in "${ADDITIONAL_PACKAGES[@]}"; do
    if pip install "$package"; then
        print_success "$package installed"
    else
        print_warning "Failed to install $package"
    fi
done

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p data/processed
mkdir -p data/raw
mkdir -p state

# Test imports
print_status "Testing Python imports..."
$PYTHON_CMD -c "
try:
    import pandas, numpy, vectorbt, yfinance
    print('✅ Core packages working')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << 'EOF'
# Alpaca API Credentials
# Get these from: https://app.alpaca.markets/account/details
APCA_API_KEY_ID=your_api_key_here
APCA_API_SECRET_KEY=your_secret_key_here

# Paper trading (recommended for testing)
APCA_API_BASE_URL=https://paper-api.alpaca.markets

# Optional settings
LOG_LEVEL=INFO
MAX_POSITION_SIZE_PCT=0.1
EOF
    print_warning "Please edit .env file with your Alpaca credentials!"
else
    print_success ".env file found"
fi

# Create startup script
print_status "Creating startup script..."
cat > start_bots.sh << 'EOF'
#!/bin/bash
# Trading Bots Startup Script

cd "$(dirname "$0")"
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
    echo "Environment variables loaded"
else
    echo "Warning: .env file not found"
    exit 1
fi

echo "Starting trading bots..."

# Start bots (uncomment the ones you want to run)
python grok/live_bots/live_gld_4h_mean_reversion.py &
# python grok/live_bots/live_slv_4h_mean_reversion.py &
# python grok/live_bots/live_xlk_1h_volatility_breakout.py &
# python grok/live_bots/live_nvda_1h_volatility_breakout.py &

echo "Bots started. Monitor with: tail -f logs/*.log"
EOF

chmod +x start_bots.sh
print_success "Startup script created"

# Create monitoring script
print_status "Creating monitoring script..."
cat > monitor_bots.sh << 'EOF'
#!/bin/bash
# Trading Bots Monitoring Script

echo "=== Trading Bots Status ==="
echo "Time: $(date)"
echo ""

# Check running processes
echo "Running bots:"
RUNNING_BOTS=$(ps aux | grep "live_.*\.py" | grep -v grep)
if [ -z "$RUNNING_BOTS" ]; then
    echo "❌ No bots currently running"
else
    echo "$RUNNING_BOTS"
fi

echo ""
echo "Bot Stop Events (last 50 lines):"
echo "=================================="
tail -50 logs/*.log 2>/dev/null | grep -i "stop\|crash\|error\|exit\|signal" | tail -10 || echo "No recent stop events found"

echo ""
echo "Recent log activity (last 10 lines):"
echo "===================================="
tail -10 logs/*.log 2>/dev/null || echo "No logs found"

echo ""
echo "System Resources:"
echo "================="
echo "Disk usage:"
df -h | grep -E "(Filesystem|/$)"
echo ""
echo "Memory usage:"
free -h

echo ""
echo "Bot Health Check:"
echo "================="
# Check if any bots have stopped recently
if [ -d "logs" ]; then
    echo "Checking for bot stop messages..."
    STOP_COUNT=$(grep -r "stopped\|crashed\|Bot stopped" logs/ 2>/dev/null | wc -l)
    ERROR_COUNT=$(grep -r "ERROR\|CRITICAL" logs/ 2>/dev/null | wc -l)

    if [ "$STOP_COUNT" -gt 0 ]; then
        echo "⚠️  $STOP_COUNT bot stop events detected"
    fi

    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "🚨 $ERROR_COUNT error messages found"
    fi

    if [ "$STOP_COUNT" -eq 0 ] && [ "$ERROR_COUNT" -eq 0 ]; then
        echo "✅ No recent stops or errors"
    fi
fi
EOF

chmod +x monitor_bots.sh
print_success "Monitoring script created"

# Final instructions
print_success "Deployment completed successfully!"
echo ""
echo "============================================="
echo "🎯 NEXT STEPS:"
echo "============================================="
echo "1. Edit .env file with your Alpaca credentials:"
echo "   nano .env"
echo ""
echo "2. Test the setup:"
echo "   source venv/bin/activate"
echo "   export \$(cat .env | xargs)"
echo "   python grok/live_bots/check_alpaca_setup.py"
echo ""
echo "3. Start your first bot:"
echo "   ./start_bots.sh"
echo ""
echo "4. Monitor performance:"
echo "   ./monitor_bots.sh"
echo "   tail -f logs/*.log"
echo ""
echo "5. For auto-start on reboot, add to crontab:"
echo "   @reboot /path/to/trading-bots/start_bots.sh"
echo ""
print_warning "⚠️  START WITH PAPER TRADING ONLY!"
print_warning "⚠️  MONITOR CLOSELY FOR THE FIRST WEEK!"
echo ""
print_success "Your trading system is ready! 🚀"

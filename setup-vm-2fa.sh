#!/bin/bash
#
# Helper script to set up 2FA authentication for VM/non-interactive use
# This script helps you get the device ID and request a verification code
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}iCloud 2FA Setup for VM/Non-Interactive Use${NC}"
echo "=================================================="
echo ""

# Check if config file exists
CONFIG_FILE="${1:-config.yaml}"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    echo "Usage: $0 [config.yaml]"
    exit 1
fi

# Extract Apple ID from config
APPLE_ID=$(python3 -c "
import yaml
import sys
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
        print(config.get('icloud', {}).get('apple_id', ''))
except Exception as e:
    sys.exit(1)
" 2>/dev/null)

if [ -z "$APPLE_ID" ]; then
    echo -e "${RED}Error: Could not read apple_id from $CONFIG_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}Apple ID:${NC} $APPLE_ID"
echo ""

# Check if Python script exists
if [ ! -f "authenticate_icloud.py" ]; then
    echo -e "${YELLOW}Warning: authenticate_icloud.py not found${NC}"
    echo "This script helps discover your trusted device ID."
    echo ""
    echo "You can still proceed by:"
    echo "1. Running the main script once interactively to see device IDs"
    echo "2. Then using environment variables for non-interactive runs"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Discover trusted devices
echo -e "${CYAN}Step 1: Discovering Trusted Devices${NC}"
echo "-------------------------------------------"
echo ""
echo "To find your trusted device ID, you can:"
echo "1. Run the authentication script interactively"
echo "2. Or check the device list from a previous run"
echo ""
echo "Example trusted devices output:"
echo "  Available trusted devices:"
echo "    0: iPhone (iPhone)"
echo "    1: MacBook Pro (Mac)"
echo ""

read -p "Do you know your trusted device ID? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}To discover your device ID, run:${NC}"
    echo "  python3 authenticate_icloud.py $APPLE_ID"
    echo ""
    echo "Or run the main script interactively once:"
    echo "  python3 main.py --config $CONFIG_FILE"
    echo ""
    echo "Note down the device number (0, 1, 2, etc.) from the list."
    echo ""
    read -p "Press Enter when you're ready to continue..."
fi

echo ""
read -p "Enter your trusted device ID (number): " DEVICE_ID

if ! [[ "$DEVICE_ID" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: Device ID must be a number${NC}"
    exit 1
fi

# Step 2: Set up environment variables
echo ""
echo -e "${CYAN}Step 2: Setting Up Environment Variables${NC}"
echo "-------------------------------------------"
echo ""

export ICLOUD_2FA_DEVICE_ID="$DEVICE_ID"
echo -e "${GREEN}✓${NC} Set ICLOUD_2FA_DEVICE_ID=$DEVICE_ID"

# Step 3: Request verification code
echo ""
echo -e "${CYAN}Step 3: Requesting Verification Code${NC}"
echo "-------------------------------------------"
echo ""
echo "To request a verification code, run:"
echo ""
echo -e "${YELLOW}  python3 main.py --config $CONFIG_FILE${NC}"
echo ""
echo "OR if you have authenticate_icloud.py:"
echo ""
echo -e "${YELLOW}  python3 authenticate_icloud.py $APPLE_ID${NC}"
echo ""
echo "The script will:"
echo "  1. Send a verification code to your trusted device"
echo "  2. Wait for you to check your device for the code"
echo "  3. You'll need to set the code as an environment variable"
echo ""

read -p "Have you already requested a code? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}Instructions:${NC}"
    echo "1. Run one of the commands above"
    echo "2. When it sends the code to your device, note the code"
    echo "3. Come back to this script and continue"
    echo ""
    read -p "Press Enter when you have requested the code..."
fi

# Step 4: Get verification code
echo ""
echo -e "${CYAN}Step 4: Enter Verification Code${NC}"
echo "-------------------------------------------"
echo ""
echo "Check your trusted device for the verification code."
echo "The code is usually 6 digits."
echo ""

read -p "Enter the verification code: " VERIFICATION_CODE

# Clean up the code (remove spaces, dashes)
VERIFICATION_CODE=$(echo "$VERIFICATION_CODE" | tr -d ' -')

if [ ${#VERIFICATION_CODE} -lt 4 ] || [ ${#VERIFICATION_CODE} -gt 8 ]; then
    echo -e "${YELLOW}Warning: Code length seems unusual (expected 4-8 digits)${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

export ICLOUD_2FA_CODE="$VERIFICATION_CODE"
echo -e "${GREEN}✓${NC} Set ICLOUD_2FA_CODE"

# Step 5: Create setup script
echo ""
echo -e "${CYAN}Step 5: Creating VM Setup Script${NC}"
echo "-------------------------------------------"
echo ""

SETUP_SCRIPT="vm-2fa-env.sh"
cat > "$SETUP_SCRIPT" << EOF
#!/bin/bash
# iCloud 2FA Environment Variables for VM
# Generated by setup-vm-2fa.sh
# 
# Usage: source vm-2fa-env.sh
# Then run: python3 main.py --config $CONFIG_FILE

export ICLOUD_2FA_DEVICE_ID="$DEVICE_ID"
export ICLOUD_2FA_CODE="$VERIFICATION_CODE"

echo "iCloud 2FA environment variables set:"
echo "  ICLOUD_2FA_DEVICE_ID=$DEVICE_ID"
echo "  ICLOUD_2FA_CODE=****** (hidden)"
EOF

chmod +x "$SETUP_SCRIPT"
echo -e "${GREEN}✓${NC} Created $SETUP_SCRIPT"
echo ""

# Step 6: Instructions for VM
echo -e "${CYAN}Step 6: Using on VM${NC}"
echo "-------------------------------------------"
echo ""
echo -e "${GREEN}Option A: Export environment variables manually${NC}"
echo "  export ICLOUD_2FA_DEVICE_ID=$DEVICE_ID"
echo "  export ICLOUD_2FA_CODE=$VERIFICATION_CODE"
echo "  python3 main.py --config $CONFIG_FILE"
echo ""
echo -e "${GREEN}Option B: Source the generated script${NC}"
echo "  source $SETUP_SCRIPT"
echo "  python3 main.py --config $CONFIG_FILE"
echo ""
echo -e "${GREEN}Option C: Use one-liner (if running immediately)${NC}"
echo "  ICLOUD_2FA_DEVICE_ID=$DEVICE_ID ICLOUD_2FA_CODE=$VERIFICATION_CODE python3 main.py --config $CONFIG_FILE"
echo ""

# Important notes
echo -e "${YELLOW}Important Notes:${NC}"
echo "  • Verification codes expire quickly (usually 10 minutes)"
echo "  • If the code expires, you'll need to request a new one"
echo "  • After successful authentication, cookies are saved"
echo "  • Future runs may not need 2FA if cookies are still valid"
echo ""

echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "To test authentication, run:"
echo -e "${CYAN}  source $SETUP_SCRIPT && python3 main.py --config $CONFIG_FILE${NC}"
echo ""


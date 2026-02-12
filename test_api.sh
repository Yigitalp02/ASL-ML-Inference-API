#!/bin/bash
# Quick API testing script
# Usage: ./test_api.sh [API_URL]

API_URL="${1:-http://localhost:8100}"

echo "=========================================="
echo "Testing ASL ML API at: $API_URL"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}[1/4] Testing /health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "$RESPONSE_BODY" | jq '.'
else
    echo -e "${RED}✗ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo "$RESPONSE_BODY"
fi
echo ""

# Test 2: Root Endpoint
echo -e "${YELLOW}[2/4] Testing / (root) endpoint...${NC}"
ROOT_RESPONSE=$(curl -s "$API_URL/")
echo "$ROOT_RESPONSE" | jq '.'
echo ""

# Test 3: Prediction with Sample Data
echo -e "${YELLOW}[3/4] Testing /predict endpoint...${NC}"
PREDICT_RESPONSE=$(curl -s -X POST "$API_URL/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5],
    "device_id": "test-script"
  }')

if echo "$PREDICT_RESPONSE" | jq -e '.letter' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Prediction successful${NC}"
    echo "$PREDICT_RESPONSE" | jq '.'
    
    LETTER=$(echo "$PREDICT_RESPONSE" | jq -r '.letter')
    CONFIDENCE=$(echo "$PREDICT_RESPONSE" | jq -r '.confidence')
    PROC_TIME=$(echo "$PREDICT_RESPONSE" | jq -r '.processing_time_ms')
    
    echo ""
    echo -e "${GREEN}Predicted Letter: $LETTER${NC}"
    echo -e "Confidence: $(awk "BEGIN {printf \"%.1f%%\", $CONFIDENCE * 100}")"
    echo -e "Processing Time: ${PROC_TIME}ms"
else
    echo -e "${RED}✗ Prediction failed${NC}"
    echo "$PREDICT_RESPONSE"
fi
echo ""

# Test 4: Statistics
echo -e "${YELLOW}[4/4] Testing /stats endpoint...${NC}"
STATS_RESPONSE=$(curl -s "$API_URL/stats")

if echo "$STATS_RESPONSE" | jq -e '.total_predictions' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Statistics retrieved${NC}"
    echo "$STATS_RESPONSE" | jq '.'
else
    echo -e "${RED}✗ Statistics failed${NC}"
    echo "$STATS_RESPONSE"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}All tests completed!${NC}"
echo "=========================================="
echo ""
echo "View interactive docs at:"
echo "  $API_URL/docs"
echo ""


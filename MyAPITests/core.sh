BASE_URL="http://localhost:5000/api/v1"
OUTPUT_FILE="MyTestResults/core.txt"

# Test 1: /health
curl -X GET ${BASE_URL}/health \
    >> $OUTPUT_FILE
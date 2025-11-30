# run scripts/initialize_example_user.sh first to ensure example user exists
BASE_URL="http://localhost:5000/api/v1"
OUTPUT_FILE="MyTestResults/search.txt"
EXAMPLE_USERNAME="public"
EXAMPLE_PASSWORD="public"

TEXT_QUERY="goldfish"
K="5"
IMAGE_QUERY_ID="1"

# Clear previous output
> $OUTPUT_FILE

# Test 1: /search/text
# Test 1.1: search by a valid text query
# login as example user to get access token, refresh token assumed not needed
TOKEN=$(curl -X POST ${BASE_URL}/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "'$EXAMPLE_USERNAME'", "password": "'$EXAMPLE_PASSWORD'"}' | jq -r '.data.access_token')

echo ${TOKEN} >> $OUTPUT_FILE

# search by a valid text query
curl -X POST ${BASE_URL}/search/text \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query": "'$TEXT_QUERY'", "k": "'$K'"}' \
    >> $OUTPUT_FILE

# Test 2: /search/image
# Test 2.1: search by a valid image
# search by a valid image
curl -X GET ${BASE_URL}/search/image/${IMAGE_QUERY_ID}/similar?k=${K} \
    -H "Authorization: Bearer $TOKEN" \
    >> $OUTPUT_FILE
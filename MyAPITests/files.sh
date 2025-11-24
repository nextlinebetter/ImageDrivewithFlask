# run scripts/initialize_public_user.sh first to ensure public user exists
BASE_URL="http://localhost:5000/api/v1"
OUTPUT_FILE="MyTestResults/files.txt"
PUBLIC_USERNAME="public"
PUBLIC_PASSWORD="public"

# Clear previous output
> $OUTPUT_FILE

# Test 1: /files/upload
# Test 1.1: upload a valid local image
# login as public user to get access token, refresh token assumed not needed
TOKEN=$(curl -X POST ${BASE_URL}/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "'$PUBLIC_USERNAME'", "password": "'$PUBLIC_PASSWORD'"}' | jq -r '.data.access_token')

echo ${TOKEN} >> $OUTPUT_FILE

# upload image
curl -X POST ${BASE_URL}/files/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@data/tiny-imagenet-200/train/n01443537/images/n01443537_0.JPEG" \
    >> $OUTPUT_FILE
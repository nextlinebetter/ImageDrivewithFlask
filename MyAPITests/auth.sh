BASE_URL="http://localhost:5173/api/v1"
OUTPUT_FILE="MyTestResults/auth.txt"
VALID_USERNAME="testuser"
VALID_PASSWORD="testpassword"
INVALID_USERNAME="aa"
INVALID_PASSWORD="bb"

# Clear previous output
> $OUTPUT_FILE

# Test 1: /auth/register
# Test 1.1: valid username and password
curl -X POST ${BASE_URL}/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username": "'$VALID_USERNAME'", "password": "'$VALID_PASSWORD'"}' \
    >> $OUTPUT_FILE

# Test 1.2: invalid username and password
curl -X POST ${BASE_URL}/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username": "'$INVALID_USERNAME'", "password": "'$INVALID_PASSWORD'"}' \
    >> $OUTPUT_FILE

# Test 2: /auth/login
# Test 2.1: correct username and password
curl -X POST ${BASE_URL}/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "'$VALID_USERNAME'", "password": "'$VALID_PASSWORD'"}' \
    >> $OUTPUT_FILE

# Test 2.2: incorrect username or password
curl -X POST ${BASE_URL}/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "'$VALID_USERNAME'", "password": "'$INVALID_PASSWORD'"}' \
    >> $OUTPUT_FILE

# Test 3: /auth/refresh
# Test 3.1: refresh when logged in
# FIXME: This test assumes a valid token is set in the Authorization header.
curl -X POST ${BASE_URL}/auth/refresh \
    -H "Content-Type: application/json" \
    >> $OUTPUT_FILE

# Test 4: /auth/me
# Test 4.1: get user info when logged in
# FIXME: This test assumes a valid token is set in the Authorization header.
curl -X GET ${BASE_URL}/auth/me \
    -H "Content-Type: application/json" \
    >> $OUTPUT_FILE
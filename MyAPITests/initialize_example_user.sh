BASE_URL="http://localhost:5000/api/v1"
EXAMPLE_USERNAME="example_user"
EXAMPLE_PASSWORD="example_user"

# register public user
curl -X POST ${BASE_URL}/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username": "'$EXAMPLE_USERNAME'", "password": "'$EXAMPLE_PASSWORD'"}'

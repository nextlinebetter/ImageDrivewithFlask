BASE_URL="http://localhost:5000/api/v1"
PUBLIC_USERNAME="public"
PUBLIC_PASSWORD="public"

# register public user
curl -X POST ${BASE_URL}/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username": "'$PUBLIC_USERNAME'", "password": "'$PUBLIC_PASSWORD'"}'

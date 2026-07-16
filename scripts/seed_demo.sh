#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000/api/v1}"

echo "Login customer..."
TOKEN=$(curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"customer@autoclaim.ai","password":"Customer@12345!"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "Create vehicle..."
VEH=$(curl -s -X POST "$API/vehicles" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"vin":"JTDBR32E720123456","registration_number":"KA01AB1234","make":"Toyota","model":"Innova","year":2020,"color":"White"}')
echo "$VEH"

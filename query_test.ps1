$response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body '{"query": "bandi", "top_k": 3}'
$response | ConvertTo-Json -Depth 10

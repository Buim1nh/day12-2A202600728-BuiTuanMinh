# Deployment Information

## Public URL
https://day122a202600728buituanminh-production.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://day122a202600728buituanminh-production.up.railway.app/health
# Expected Response:
# {"status": "ok", "version": "1.0.0", "environment": "production", "checks": {"redis": true}}
```

### Readiness Check
```bash
curl https://day122a202600728buituanminh-production.up.railway.app/ready
# Expected Response:
# {"ready": true}
```

### API Test (with authentication)
```bash
curl -X POST https://day122a202600728buituanminh-production.up.railway.app/ask \
  -H "X-API-Key: your-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_01", "question": "What is Docker?"}'

# Expected Response:
# {"question": "What is Docker?", "answer": "Container là cách đóng gói app để chạy ở mọi nơi...", "model": "gpt-4o-mini", "timestamp": "..."}
```

### Rate Limiting Verification
```bash
# Send 15 consecutive requests to trigger the 429 Rate Limit
for i in {1..15}; do 
  curl -X POST https://day122a202600728buituanminh-production.up.railway.app/ask \
    -H "X-API-Key: your-secret-api-key" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test_user_01", "question": "Test request"}'
  echo ""
done

# Expected Response near request 11+:
# {"detail": "Rate limit exceeded: 10 req/min"}
```

## Environment Variables Set
- `PORT` = `8000` (auto-configured by Railway)
- `ENVIRONMENT` = `production`
- `APP_NAME` = `Production AI Agent`
- `AGENT_API_KEY` = `your-secret-api-key`
- `JWT_SECRET` = `your-jwt-secret-key-string`
- `REDIS_URL` = `redis://default:password@host:port/0`
- `RATE_LIMIT_PER_MINUTE` = `10`
- `DAILY_BUDGET_USD` = `5.0`
- `MONTHLY_BUDGET_USD` = `10.0`

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

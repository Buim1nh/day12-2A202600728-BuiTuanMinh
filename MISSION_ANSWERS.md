# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `develop/app.py`
1. **Hardcoded Secrets**: The OpenAI API key (`OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"`) and Database credentials (`DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`) are hardcoded, making them visible to anyone with access to the source code or repository.
2. **Lack of Configuration Management**: Configuration flags like `DEBUG = True` and variables like `MAX_TOKENS = 500` are hardcoded in the script instead of being loaded from environment variables (violating the 12-Factor App design).
3. **Improper Logging**: Standard Python `print()` statements are used instead of structured logger objects. Furthermore, a sensitive API key is logged to stdout (`print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`).
4. **Missing Health Probes**: There are no health check endpoints (`/health` or `/ready`). An orchestration system or platform won't be able to detect if the application is dead or stuck.
5. **Fixed Network Binding**: The application binds to `localhost` and a fixed port `8000` inside `uvicorn.run()`. In production cloud platforms (like Render or Railway), we must bind to `0.0.0.0` and allow the port to be dynamically set via the `PORT` environment variable.
6. **Reload mode active**: `reload=True` is enabled which degrades production performance and introduces security risks.

### Exercise 1.3: Comparison table
| Feature | Basic (Develop) | Advanced (Production) | Tại sao quan trọng? |
|---------|-----------------|-----------------------|---------------------|
| **Config** | Hardcode | Env vars / Config class | Đảm bảo tính linh động giữa các môi trường (Dev/Staging/Prod) mà không phải thay đổi mã nguồn; tránh rò rỉ keys bảo mật khi push code lên Git. |
| **Health check** | Không có | `/health` & `/ready` | Giúp hệ thống giám sát (Railway/Kubernetes/Render) kiểm tra tình trạng ứng dụng để tự động khởi động lại hoặc tạm ngắt định tuyến traffic khi xảy ra lỗi. |
| **Logging** | `print()` | Structured JSON logging | Cho phép thu thập, lọc và phân tích log tự động qua các công cụ log aggregator tập trung (Datadog, Loki, Elastic), tránh in thông tin nhạy cảm. |
| **Shutdown** | Đột ngột | Graceful shutdown | Cho phép ứng dụng đóng kết nối cơ sở dữ liệu và hoàn thành nốt các request đang xử lý (in-flight requests) trước khi tắt tiến trình, hạn chế lỗi mất dữ liệu. |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base Image**: In development, `python:3.11` (full Debian installation with development tools like compilers and headers, ~1GB). In production, `python:3.11-slim` (minimal runtime Debian, ~120MB).
2. **Working Directory**: `/app` is set as the starting directory inside the container for all subsequent COPY, RUN, and CMD operations.
3. **Copy requirements first**: This utilizes Docker's layer caching. Since dependencies change less frequently than code, caching this layer reduces future image build times dramatically.
4. **CMD vs ENTRYPOINT**: `ENTRYPOINT` defines the main executable tool configured for the container. `CMD` provides the default arguments passed to this executable, which can easily be overridden at runtime.

### Exercise 2.3: Image size comparison
- **Develop (Single-stage)**: ~1.01 GB
- **Production (Multi-stage)**: ~141 MB
- **Difference**: ~86% reduction in size.

### Exercise 2.4: Docker Compose stack
**Architecture diagram:**
```
[ Client ] -> Port 80 -> [ Nginx Load Balancer ]
                                |
             +------------------+------------------+
             | (Round Robin)    |                  |
             v                  v                  v
       [ Agent Rep 1 ]    [ Agent Rep 2 ]    [ Agent Rep 3 ]
       (Port 8000)        (Port 8000)        (Port 8000)
             |                  |                  |
             +------------------+------------------+
                                v
                   [ Redis Instance (Port 6379) ]
```
- **Services started**: `nginx` (Port 80, acts as load balancer), `agent` (scaled up to 3 replicas running on port 8000), and `redis` (Port 6379, stores states).
- **Communication**: Services are attached to the same Docker container network, letting them communicate securely using their service hostnames (`redis`, `agent`).

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- **Public URL**: https://day122a202600728buituanminh-production.up.railway.app
- **Config comparison (`railway.toml` vs `render.yaml`)**:
  - `railway.toml` is a platform-specific build and deploy instruction sheet for the Railway CLI. It defines properties like the builder to use (DOCKERFILE) and startup settings.
  - `render.yaml` is a declarative Render Blueprint spec. It describes not just service deployments but also multi-tier infrastructure configurations (like provisioning Redis side-by-side with web services) directly from Git.

---

## Part 4: API Security

### Exercise 4.1-4.3: Test results
- **No API Key Request**:
  - Command: `curl http://localhost:8000/ask -X POST -d '{"question":"Hello"}'`
  - Output: `401 Unauthorized` with body `{"detail": "Invalid or missing API key. Include header: X-API-Key: <key>"}`.
- **Valid API Key Request**:
  - Command: `curl -H "X-API-Key: secret" http://localhost:8000/ask -X POST -d '{"question":"What is Docker?"}'`
  - Output: `200 OK` with JSON answer:
    `{"question": "What is Docker?", "answer": "Container là cách đóng gói app để chạy ở mọi nơi...", "model": "gpt-4o-mini", "timestamp": "..."}`
- **Rate limiting algorithm**: Sliding Window Counter.
  - Limit configured: 10 requests per minute per user.
  - Hit limit output: `429 Too Many Requests` with header `Retry-After: 60`.

### Exercise 4.4: Cost guard implementation
- **Approach**: Calculates estimated input/output costs before and after calling the LLM based on token pricing (e.g., $0.00015/1K input, $0.0006/1K output).
- **State management**: Costs are stored in Redis using the key pattern `cost:<user_id>:<YYYY-MM>`. If the monthly cumulative cost exceeds the budget limit (e.g., $10), a `402 Payment Required` error is returned to block further API consumption.

---

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
- **Health & Readiness checks**:
  - `/health`: Liveness probe. Returns `200` to indicate the FastAPI service process is active, verifying the Redis link if configured.
  - `/ready`: Readiness probe. Returns `200` only after successfully completing internal startups and establishing connections to Redis. If Redis is down, it returns `503 Service Unavailable`.
- **Graceful Shutdown**:
  - Listens for the `SIGTERM` signal. Uvicorn finishes current in-flight requests, stops accepting new incoming traffic, closes active socket connections gracefully, and terminates.
- **Stateless design**:
  - The agent holds no state (conversation history, rate limit timers, user budgets) in localized application memories. Everything is stored in the external `redis` container. This allows load balancers to distribute requests arbitrarily across replicas without losing user session contexts.

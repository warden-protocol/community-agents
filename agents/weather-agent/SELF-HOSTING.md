# Self-Hosting Guide

Deploy the Weather Agent on your own infrastructure using Docker.

## Quick Start (No Databases)

**For stateless weather queries - the simplest deployment!**

This agent responds to instant requests without needing persistent conversation history. Perfect for quick weather lookups and stateless API responses.

### Prerequisites

- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Your API keys ready:
  - WeatherAPI key from [weatherapi.com](https://www.weatherapi.com/signup.aspx)
  - OpenAI API key from [platform.openai.com](https://platform.openai.com/)

### Setup

1. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:
   ```bash
   WEATHER_API_KEY=your_actual_weather_api_key
   OPENAI_API_KEY=your_actual_openai_api_key
   AGENT_API_KEY=your_secure_agent_api_key
   ```

   **Generate a secure API key:**
   ```bash
   # On macOS/Linux
   openssl rand -base64 32

   # Or use a strong random password
   ```

2. **Start the agent:**
   ```bash
   docker compose up -d
   ```

3. **Access Studio UI:**
   - Go to [https://smith.langchain.com/studio](https://smith.langchain.com/studio)
   - Click "Connect to Server"
   - Enter: `http://localhost:8000`
   - **Add authentication header:**
     - Click on "Headers" or "Advanced"
     - Add header: `x-api-key: your_secure_agent_api_key`
   - Start asking weather questions!

### Managing Your Deployment

```bash
# View logs
docker compose logs -f

# Stop the agent
docker compose stop

# Remove completely
docker compose down
```

---

## Adding Persistent History

**Enable conversation history that survives restarts.**

Use persistent storage if you need multi-turn conversations, conversation history across restarts, or separate conversation threads.

### Setup

1. **Start full stack (Agent + Redis + PostgreSQL):**
   ```bash
   docker compose -f docker-compose.full.yml up -d
   ```

2. **Verify services are healthy:**
   ```bash
   docker compose -f docker-compose.full.yml ps
   ```

3. **Test persistence:**
   - Ask a question in Studio
   - Restart: `docker compose -f docker-compose.full.yml restart weather-agent`
   - Reconnect - your conversation history is preserved!

### Managing the Full Stack

```bash
# View logs
docker compose -f docker-compose.full.yml logs -f

# Stop all services
docker compose -f docker-compose.full.yml down

# Remove all data (⚠️ deletes conversation history)
docker compose -f docker-compose.full.yml down -v
```

### Backup

```bash
# Backup database
docker compose -f docker-compose.full.yml exec postgres pg_dump \
  -U langgraph langgraph > backup-$(date +%Y%m%d).sql

# Restore
docker compose -f docker-compose.full.yml exec -T postgres psql \
  -U langgraph langgraph < backup-20250107.sql
```

---

## Security

### API Key Authentication

The agent is protected with API key authentication. All requests must include the `x-api-key` header:

```bash
# Test with curl
curl -H "x-api-key: your_secure_agent_api_key" http://localhost:8000/
```

**Security Best Practices:**
- ✅ Generate a strong, random API key (use `openssl rand -base64 32`)
- ✅ Keep your API key secret (never commit `.env` to git)
- ✅ Rotate keys periodically
- ✅ Use HTTPS in production (not covered in this setup)
- ⚠️ If `AGENT_API_KEY` is not set, authentication is disabled (not recommended!)

---

## Configuration

All configuration via `.env` file:

```bash
# Required
WEATHER_API_KEY=your_weather_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
AGENT_API_KEY=your_secure_agent_api_key  # For protecting your agent

# Optional
MODEL_NAME=gpt-4o-mini              # AI model (gpt-4o, gpt-3.5-turbo)
TEMPERATURE=0                        # Response creativity (0-1)
POSTGRES_PASSWORD=secure_password    # Change in production!
```

**Change default port:**
Edit `docker-compose.yml`:
```yaml
services:
  weather-agent:
    ports:
      - "3000:8000"  # Access on port 3000
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Change port in docker-compose.yml
ports:
  - "8001:8000"
```

### Cannot Connect to the Agent
1. Check container is running: `docker compose ps`
2. Check logs: `docker compose logs weather-agent`
3. Test connection: `curl -H "x-api-key: your_api_key" http://localhost:8000/`
4. Verify you're providing the correct `x-api-key` header

### Build Failures
```bash
# Clean build
docker compose build --no-cache

# Check disk space
df -h
```

### Database Connection Errors
```bash
# Check Postgres health
docker compose -f docker-compose.full.yml ps postgres

# Test connection
docker compose -f docker-compose.full.yml exec postgres \
  psql -U langgraph -c "SELECT 1"

# View logs
docker compose -f docker-compose.full.yml logs postgres
```

### Agent Returns Errors
1. Check API keys: `docker compose exec weather-agent env | grep API_KEY`
2. Verify keys are valid at provider websites
3. Check rate limits
4. Review logs: `docker compose logs -f weather-agent`

---

## Deployment Comparison

| Feature | Simple | Full Stack |
|---------|--------|------------|
| **Containers** | 1 (agent) | 3 (agent + Redis + Postgres) |
| **Startup** | ~10 seconds | ~30 seconds |
| **Memory** | ~200MB | ~500MB |
| **Persistent History** | ❌ | ✅ |
| **Best For** | Quick queries | Multi-turn conversations |

---

## Resources

- [Main README](README.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Docker Documentation](https://docs.docker.com/)

**Ready to deploy?** Start with the [Quick Start](#quick-start-no-databases) above!

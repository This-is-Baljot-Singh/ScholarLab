# MongoDB Setup - Local vs Docker

## Quick Start

### Option 1: Local Development (uvicorn)

1. **Install MongoDB locally** (if not already installed):
   ```bash
   # macOS
   brew install mongodb-community
   brew services start mongodb-community
   
   # Linux (Ubuntu/Debian)
   sudo apt-get install -y mongodb
   sudo systemctl start mongodb
   
   # Windows - download from https://www.mongodb.com/try/download/community
   ```

2. **Copy the local environment file**:
   ```bash
   cd backend
   cp .env.local .env
   ```

3. **Run the backend server**:
   ```bash
   # From backend directory
   uvicorn app.main:app --reload
   ```

4. **Seed test users** (in another terminal):
   ```bash
   cd backend
   python seed_users.py
   ```

### Option 2: Docker Compose (Full Stack)

1. **Copy the Docker environment file**:
   ```bash
   cd backend
   cp .env.docker .env
   ```

2. **Start MongoDB and Redis with Docker**:
   ```bash
   # From project root
   docker-compose up mongodb redis -d
   ```

3. **Run the backend server with uvicorn**:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

4. **Seed test users** (in another terminal):
   ```bash
   cd backend
   python seed_users.py
   ```

### Option 3: Full Docker Stack

1. **Copy the Docker environment file**:
   ```bash
   cd backend
   cp .env.docker .env
   ```

2. **Start everything with Docker Compose**:
   ```bash
   # From project root
   docker-compose up
   ```

## Environment Variables

| Variable | Local Default | Docker Default |
|----------|---------------|----------------|
| `MONGODB_URL` | `mongodb://localhost:27017` | `mongodb://admin:admin@mongodb:27017` |
| `DATABASE_NAME` | `scholarlab` | `scholarlab` |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` |

## Switching Between Configurations

```bash
# Use local MongoDB
cp .env.local .env
uvicorn app.main:app --reload

# Use Docker MongoDB
cp .env.docker .env
# Make sure Docker containers are running first
docker-compose up mongodb redis -d
uvicorn app.main:app --reload
```

## Troubleshooting

**Connection Refused (localhost:27017)**
- Local MongoDB not running: `brew services start mongodb-community` (macOS) or `sudo systemctl start mongodb` (Linux)
- Using wrong `.env` file - check which one is active

**Connection Refused (mongodb:27017)**
- Docker containers not running: `docker-compose up mongodb -d`
- Using wrong `.env` file - should be `.env.docker`

**Permission Denied (mongodb authentication)**
- Using `.env.local` with Docker - Docker MongoDB requires auth credentials
- Using `.env.docker` with local MongoDB - local doesn't have auth by default

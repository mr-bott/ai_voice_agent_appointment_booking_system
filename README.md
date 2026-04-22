# Real-Time Multilingual Voice AI Agent for Clinical Appointment Booking

A production-grade, low-latency voice AI agent that handles healthcare appointment workflows through natural voice conversations.

## Features
- **Real-time Interaction:** End-to-end latency targeted under 450ms.
- **Multilingual Support:** English, Hindi, and Tamil (auto-detects and responds in the user's language).
- **True Tool Calling:** Dynamically queries doctor availability and books appointments via database queries.
- **Interrupt / Barge-in:** Immediately stops speaking and listens when the user interrupts.
- **Outbound Campaigns:** Capable of making outbound reminder calls using a Celery task queue.

## Architecture

```mermaid
graph TD
    Client[Next.js Client] <-->|WebSocket: Audio In/Out| Backend[FastAPI Server]
    
    subgraph Backend Services
        Backend -->|Audio Stream| STT[Deepgram STT]
        STT -->|Transcript| Agent[LLM Agent + Tool Router]
        Agent -->|Tool Calls| Tools[Tool Executor]
        Tools -->|Query/Mutation| DB[(PostgreSQL)]
        Tools -->|Query/Mutation| Cache[(Redis)]
        Agent -->|Response Text| TTS[TTS Engine]
        TTS -->|Audio Stream| Backend
    end
    
    subgraph Jobs
        Celery[Celery Worker] -->|Fetch Campaigns| DB
    end
```

## Setup Instructions

### 1. Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.10+
- API Keys: OpenAI (or compatible), Deepgram (optional, will mock without), ElevenLabs (optional, using Edge-TTS by default).

### 2. Environment Variables
Create a `.env` file in the `backend/` directory:
```env
# docker - PostgreSql
DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/voice_agent 
# docker - Redis
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=""
DEEPGRAM_API_KEY=""
```

### 3. Run with Docker
```bash
D:\voice-agent> docker-compose up -d
```
This starts PostgreSQL and Redis.

### 4. Run Backend
```bash
D:\voice-agent> cd backend
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirements.txt

#important to come abck to global level
cd ..
D:\voice-agent> python -m uvicorn backend.main:app --reload
                     
                                                                                                 
```

### 5. Run Frontend
```bash
D:\voice-agent> cd frontend
npm install
npm run dev
```

### 6. Run Celery Worker (for Outbound Campaigns)
```bash
cd backend
celery -A scheduler.celery_app worker --loglevel=info
```

## Why this Tech Stack?
- **FastAPI:** Essential for high-performance, async WebSocket handling needed for low-latency audio streaming.
- **PostgreSQL + Redis:** Postgres handles persistent patient history, while Redis powers lightning-fast session memory and Celery task queues.
- **Next.js + Tailwind:** Delivers a premium, recruiter-impressive UI quickly.
- **Deepgram + OpenAI + Edge-TTS/ElevenLabs:** The perfect combination for sub-500ms voice interactions. Deepgram provides real-time streaming STT, OpenAI processes tool calls, and TTS streams chunks back to the client.

## Memory Strategy
1. **Session Memory (Redis):** Stores the current conversational context, maintaining the context window for the LLM. Automatically expires after an hour to save resources.
2. **Persistent Memory (PostgreSQL):** Stores patient profiles, language preferences, and appointment history. Injected into the system prompt when a returning patient is identified.

## Latency Breakdown
- **STT (Deepgram):** ~100-150ms
- **LLM (OpenAI gpt-4o-mini):** ~200-250ms for first token
- **TTS (Edge TTS streaming):** ~50-100ms for first audio chunk
- **Total:** ~350-500ms

## Scaling & Tradeoffs
- **Horizontal Scaling:** The backend can be scaled horizontally behind a load balancer (like Nginx/HAProxy) using sticky sessions for WebSockets, or utilizing Redis Pub/Sub to sync states across instances.
- **Limitations:** Edge TTS is used as a fallback for free tier, but ElevenLabs WebSocket streaming is recommended for true ultra-low latency and hyper-realistic voices in production.

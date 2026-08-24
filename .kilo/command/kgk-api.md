---
description: Start the KGK FastAPI development server
agent: kgk-architect
---
Start the KGK API server with uvicorn.

$ARGUMENTS are passed to `uvicorn`.

Examples:
- `/kgk-api` — start with reload
- `/kgk-api --port 8080` — custom port

Command:
```bash
uvicorn api.app:app --reload $ARGUMENTS
```

After starting, verify the health endpoint: `curl http://127.0.0.1:8000/health`

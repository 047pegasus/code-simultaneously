# Collaborative Code Editor

Real-time collaborative code editor with AI autocomplete suggestions, built with **FastAPI**, **WebSockets**, and a **PostgreSQL (or SQLAlchemy-compatible) database** for room state.

## Features

- **Create & join rooms** via simple room IDs
- **Real-time code synchronization** using WebSockets (last-write-wins)
- **Mocked AI autocomplete** with a `/autocomplete` POST endpoint
- **Room state persisted in a database** via SQLAlchemy models
- **Clean project structure** with routers, services, and a small frontend

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure the database URL (PostgreSQL recommended):
   ```bash
   export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/collab_db"
   ```
   If `DATABASE_URL` is not set, the app falls back to a local SQLite file `app.db` for convenience.
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
6. Open the editor UI at:
   ```text
   http://localhost:8000/
   ```

## API & WebSocket Endpoints

- `POST /api/rooms`  
  Creates a new room. Returns:
  ```json
  { "roomId": "<uuid>" }
  ```

- `POST /api/autocomplete`  
  Mocked autocomplete endpoint. Example request body:
  ```json
  {
    "code": "print('hello worl')",
    "cursorPosition": 18,
    "language": "python"
  }
  ```

- `GET /`  
  Serves the collaborative editor HTML page.

- `WS /ws/{room_id}`  
  WebSocket endpoint for real-time code updates for the given room.

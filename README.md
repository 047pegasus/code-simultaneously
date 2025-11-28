# Collaborative Code Editor

A real-time collaborative code editor with AI autocomplete suggestions, built with FastAPI and WebSockets.

## Features

- Create and join rooms for collaborative coding
- Real-time code synchronization using WebSockets
- Simple AI-powered code autocomplete
- In-memory room state management
- Clean project structure with FastAPI routers

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
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

- `POST /rooms` - Create a new room
- `POST /autocomplete` - Get code completion suggestions
- `GET /room/{room_id}` - Join a room (WebSocket endpoint at `/ws/{room_id}`)

## Development

To run tests:
```bash
pytest
```
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, Set, Optional
import uuid
import json
import os
from pathlib import Path

# Create the FastAPI app
app = FastAPI(title="Collaborative Code Editor")

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up static files and templates
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# In-memory storage for rooms and their active connections
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.room_contents: Dict[str, str] = {}
        self.room_languages: Dict[str, str] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.room_contents[room_id] = ""
            self.room_languages[room_id] = "python"  # Default language
            
        self.rooms[room_id].add(websocket)
        
        # Send current room content to the new user
        await websocket.send_text(
            json.dumps({
                "type": "sync", 
                "content": self.room_contents[room_id],
                "language": self.room_languages[room_id]
            })
        )

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                del self.room_contents[room_id]

    async def broadcast(self, room_id: str, message: str, sender: WebSocket = None):
        if room_id in self.rooms:
            for connection in self.rooms[room_id]:
                if connection != sender:  # Don't send back to the sender
                    await connection.send_text(message)

room_manager = RoomManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "room_id": None})

@app.get("/room/{room_id}", response_class=HTMLResponse)
async def read_room(request: Request, room_id: str):
    return templates.TemplateResponse("index.html", {"request": request, "room_id": room_id})

@app.post("/api/rooms")
async def create_room():
    room_id = str(uuid.uuid4())
    return {"room_id": room_id}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await room_manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "update":
                # Update the room's content
                room_manager.room_contents[room_id] = message["content"]
                # Update language if provided
                if "language" in message:
                    room_manager.room_languages[room_id] = message["language"]
                
                # Broadcast the update to all other clients
                await room_manager.broadcast(
                    room_id,
                    json.dumps({
                        "type": "update",
                        "content": message["content"],
                        "cursor_position": message.get("cursor_position"),
                        "language": room_manager.room_languages.get(room_id, "python")
                    }),
                    sender=websocket
                )
                
            elif message["type"] == "cursor_move":
                # Broadcast cursor movement to other clients
                await room_manager.broadcast(
                    room_id,
                    json.dumps({
                        "type": "cursor_move",
                        "cursor_position": message["cursor_position"],
                        "user_id": message.get("user_id", "anonymous")
                    }),
                    sender=websocket
                )
                
    except WebSocketDisconnect:
        room_manager.disconnect(room_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        room_manager.disconnect(room_id, websocket)

@app.post("/autocomplete")
async def get_autocomplete_suggestion(code: str, cursor_position: int, language: str = "python"):
    try:
        # Simple rule-based autocomplete suggestions based on the current line
        lines = code.split('\n')
        current_line = ''
        current_line_num = 0
        
        # Find the current line based on cursor position
        for i, line in enumerate(lines):
            if cursor_position <= len(line) + (1 if i > 0 else 0):
                current_line = line
                current_line_num = i
                break
            cursor_position -= len(line) + 1  # +1 for newline character
        
        # Get the current word being typed
        current_word = ''
        if current_line:
            # Get the text before the cursor
            text_before_cursor = current_line[:cursor_position]
            # Find the start of the current word
            word_start = max(text_before_cursor.rfind(' '), 
                           text_before_cursor.rfind('\t'),
                           text_before_cursor.rfind('('),
                           text_before_cursor.rfind('['),
                           text_before_cursor.rfind('{')) + 1
            current_word = text_before_cursor[word_start:]
        
        # Language-specific suggestions
        suggestions = []
        
        # Python specific suggestions
        if language.lower() == 'python':
            python_keywords = [
                'def ', 'class ', 'if ', 'else:', 'elif ', 'for ', 'while ', 'try:', 
                'except ', 'finally:', 'with ', 'import ', 'from ', 'as ', 'return ',
                'yield ', 'async ', 'await ', 'raise ', 'pass', 'break', 'continue',
                'True', 'False', 'None', 'and ', 'or ', 'not ', 'in ', 'is ', 'lambda '
            ]
            
            # Filter suggestions based on current word
            if current_word:
                suggestions = [kw for kw in python_keywords if kw.startswith(current_word)]
            
            # If no keyword matches, check for common patterns
            if not suggestions:
                if current_line.strip().endswith('prin'):
                    suggestions = ['print()']
                elif current_line.strip().endswith('def '):
                    suggestions = ['def function_name():']
                elif current_line.strip().endswith('for '):
                    suggestions = ['for i in range():', 'for item in collection:']
                elif current_line.strip().endswith('if '):
                    suggestions = ['if :', 'if condition:']
                elif current_line.strip().endswith('while '):
                    suggestions = ['while :', 'while condition:']
                elif current_line.strip().endswith('class '):
                    suggestions = ['ClassName:', 'ClassName(object):']
                elif current_line.strip().endswith('import '):
                    suggestions = ['os', 'sys', 'json', 'typing', 'fastapi', 'pydantic']
        
        # If still no suggestions, provide some general ones
        if not suggestions:
            suggestions = [
                'print()', 'def ', 'for ', 'if ', 'while ', 'class ',
                'import ', 'from ', 'try:', 'except ', 'finally:'
            ]
        
        # Return the first 5 suggestions
        return {
            "suggestions": suggestions[:5],
            "cursor_position": cursor_position
        }
        
    except Exception as e:
        print(f"Autocomplete error: {e}")
        return {"suggestions": [], "cursor_position": cursor_position}

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable or use default 8000
    port = int(os.environ.get("PORT", 8000))
    
    # Run the FastAPI application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
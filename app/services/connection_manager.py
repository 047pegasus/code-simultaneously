from fastapi import WebSocket
from typing import Dict, List, Set
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_rooms: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, room_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_rooms[client_id] = room_id
    
    def disconnect(self, client_id: str):
        if client_id in self.client_rooms:
            del self.client_rooms[client_id]
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def broadcast(self, message: dict, room_id: str, exclude: set = None):
        if exclude is None:
            exclude = set()
        
        for client_id, connection in self.active_connections.items():
            if (self.client_rooms.get(client_id) == room_id and 
                client_id not in exclude):
                try:
                    await connection.send_json(message)
                except:
                    self.disconnect(client_id)

manager = ConnectionManager()

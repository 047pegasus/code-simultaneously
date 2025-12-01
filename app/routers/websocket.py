# app/routers/websocket.py
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.connection_manager import manager
from ..services.room_service import room_service


router = APIRouter()


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for real-time collaborative editing.

    - Validates that the room exists in the database.
    - Sends the current document content to the newly connected client.
    - Broadcasts subsequent edits to all other participants in the room.
    """
    client_id = str(uuid.uuid4())

    # Ensure room exists in the database
    room = room_service.get_room(room_id)
    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return

    await manager.connect(websocket, client_id, room_id)

    # Send initial content to the newly connected client
    await manager.send_message(
        {"type": "code_sync", "content": room.content or "", "client_id": client_id},
        client_id,
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "code_update":
                content = message.get("content", "")
                # Persist latest content (last-write-wins)
                room_service.update_room_content(room_id, content)

                # Broadcast the update to all other clients in the room
                await manager.broadcast(
                    {
                        "type": "code_update",
                        "content": content,
                        "client_id": client_id,
                    },
                    room_id,
                    {client_id},
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(
            {
                "type": "user_left",
                "client_id": client_id,
            },
            room_id,
        )
    except Exception as e:
        # Log and clean up on unexpected error, but don't crash the server
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)
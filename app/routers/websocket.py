# app/routers/websocket.py
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.connection_manager import manager
from ..services.ot_service import Operation, ot_service
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

    # Send initial content + version to the newly connected client
    await manager.send_message(
        {
            "type": "code_sync",
            "content": room.content or "",
            "version": room.version,
        },
        client_id,
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "op":
                # Client sends a single contiguous operation with a base_version
                op_data = message.get("op") or {}
                base_version = int(op_data.get("baseVersion", 0))
                op = Operation(
                    type=op_data.get("type", "insert"),
                    index=int(op_data.get("index", 0)),
                    length=int(op_data.get("length", 0)),
                    text=op_data.get("text", ""),
                    base_version=base_version,
                )

                # Reload the latest room state
                current_room = room_service.get_room(room_id)
                if not current_room:
                    continue

                # Transform operation against any concurrent history
                transformed = ot_service.transform_against_history(
                    room_id, op, current_room.version
                )

                # Apply to content and persist
                new_content = ot_service.apply_operation(
                    current_room.content or "", transformed
                )
                new_version = current_room.version + 1
                room_service.update_room_content(room_id, new_content, new_version)

                # Record the operation with the new base_version
                ot_service.record_operation(
                    room_id,
                    Operation(
                        type=transformed.type,
                        index=transformed.index,
                        length=transformed.length,
                        text=transformed.text,
                        base_version=new_version,
                    ),
                )

                # Broadcast the transformed op to all other clients (not the sender)
                await manager.broadcast(
                    {
                        "type": "op",
                        "op": {
                            "type": transformed.type,
                            "index": transformed.index,
                            "length": transformed.length,
                            "text": transformed.text,
                            "baseVersion": new_version,
                        },
                    },
                    room_id,
                    exclude={client_id},
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
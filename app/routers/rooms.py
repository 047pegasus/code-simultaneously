# app/routers/rooms.py
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.room_service import room_service


router = APIRouter()


class RoomCreate(BaseModel):
    # Optional friendly name; backend will fall back to "Untitled Room"
    name: str | None = None


@router.post("/rooms")
async def create_room(room_data: RoomCreate | None = None):
    """
    Create a new room and return its ID.

    Request body is optional; if omitted we still create an unnamed room.
    """
    name = (room_data.name if room_data else None) or "Untitled Room"
    room = room_service.create_room(name)
    return {"roomId": room["id"]}
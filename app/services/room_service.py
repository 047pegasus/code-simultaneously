from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from ..internal.database import SessionLocal
from ..models.document import Document


class RoomService:
    """
    Service layer for creating and managing rooms/documents.

    Backed by a relational database so room state is persisted.
    """

    def _create_session(self) -> Session:
        return SessionLocal()

    def create_room(self, name: str) -> dict:
        """
        Create a new room + backing document and return a simple dict
        that can be safely serialized.
        """
        db = self._create_session()
        try:
            room_id = str(uuid4())
            doc = Document(
                id=room_id, name=name or "Untitled Room", content="", version=0
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            return {
                "id": doc.id,
                "name": doc.name,
                "content": doc.content,
                "version": doc.version,
                "created_at": doc.created_at,
            }
        finally:
            db.close()

    def get_room(self, room_id: str) -> Optional[Document]:
        db = self._create_session()
        try:
            return db.query(Document).filter(Document.id == room_id).first()
        finally:
            db.close()

    def update_room_content(
        self, room_id: str, content: str, version: Optional[int] = None
    ) -> bool:
        db = self._create_session()
        try:
            doc = db.query(Document).filter(Document.id == room_id).first()
            if not doc:
                return False
            doc.content = content
            if version is not None:
                doc.version = version
            db.commit()
            return True
        finally:
            db.close()


room_service = RoomService()
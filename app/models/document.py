from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from ..internal.database import Base


class Document(Base):
    """
    Simple document model used as the backing store for a room.

    We treat the document's primary key as the room ID exposed to clients.
    """

    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="")
    version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
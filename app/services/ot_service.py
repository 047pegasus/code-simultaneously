from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Operation:
    """
    A very small OT operation model for a single contiguous change.

    type: "insert" | "delete" | "replace"
    index: character index in the document
    length: number of characters affected (0 for pure insert)
    text: text to insert/replace with ("" for pure delete)
    base_version: document version on which this op was based
    """

    type: str
    index: int
    length: int
    text: str
    base_version: int


class OTService:
    """
    Simple in-memory OT service.

    - We keep a short history of operations per room.
    - When a client submits an operation with base_version < current_version,
      we transform it against the subsequent operations.
    - We then apply the transformed op to the document content.
    """

    def __init__(self, history_limit: int = 100):
        self._history: Dict[str, List[Operation]] = {}
        self._history_limit = history_limit

    def _get_history(self, room_id: str) -> List[Operation]:
        return self._history.setdefault(room_id, [])

    def record_operation(self, room_id: str, op: Operation) -> None:
        history = self._get_history(room_id)
        history.append(op)
        if len(history) > self._history_limit:
            # Keep only the most recent operations
            del history[: len(history) - self._history_limit]

    def transform_against_history(
        self, room_id: str, op: Operation, current_version: int
    ) -> Operation:
        """
        Transform an operation from base_version up to current_version.
        This is a very small, line-based OT that handles contiguous inserts/deletes.
        """
        history = self._get_history(room_id)
        # Only consider operations that happened after the base version
        later_ops = [h for h in history if h.base_version >= op.base_version]

        index = op.index
        for other in later_ops:
            if other.type == "insert":
                if other.index <= index:
                    index += len(other.text)
            elif other.type == "delete":
                if other.index < index:
                    # Characters deleted before our index shift it left
                    shift = min(other.length, index - other.index)
                    index -= shift

        return Operation(
            type=op.type,
            index=index,
            length=op.length,
            text=op.text,
            base_version=current_version,
        )

    @staticmethod
    def apply_operation(content: str, op: Operation) -> str:
        if op.type == "insert":
            return content[: op.index] + op.text + content[op.index :]
        if op.type == "delete":
            return content[: op.index] + content[op.index + op.length :]
        if op.type == "replace":
            return content[: op.index] + op.text + content[op.index + op.length :]
        # Fallback: no-op
        return content


ot_service = OTService()



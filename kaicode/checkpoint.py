"""File-change checkpoints — undo/redo for everything the agent writes.

Every edit_file / create_file is wrapped: KaiCode snapshots the file's content
*before* the change and *after*, so any agent action is reversible. This is the
safety net that makes it comfortable to let a local model run with auto-approval
— if it mangles a file, `/undo` puts it back exactly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Change:
    path: str
    before: str | None  # None  → file did not exist before (it was created)
    after: str | None  # None  → file was removed by the change
    tool: str
    ts: float = field(default_factory=time.time)

    @property
    def label(self) -> str:
        if self.before is None:
            return "created"
        if self.after is None:
            return "deleted"
        return "edited"


class CheckpointStack:
    """In-session undo/redo of agent file changes."""

    def __init__(self) -> None:
        self._undo: list[Change] = []
        self._redo: list[Change] = []
        self._snapshots: dict[str, list[Change]] = {}

    @staticmethod
    def snapshot(path: str) -> str | None:
        """Current content of a file, or None if it doesn't exist."""
        p = Path(path)
        try:
            return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
        except Exception:
            return None

    def record(self, path: str, before: str | None, after: str | None, tool: str) -> None:
        # No-op changes (content unchanged) aren't worth a checkpoint.
        if before == after:
            return
        self._undo.append(Change(path, before, after, tool))
        self._redo.clear()  # a new change invalidates the redo branch

    @staticmethod
    def _restore(path: str, content: str | None) -> None:
        p = Path(path)
        if content is None:
            if p.exists():
                p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def undo(self) -> Change | None:
        if not self._undo:
            return None
        ch = self._undo.pop()
        self._restore(ch.path, ch.before)
        self._redo.append(ch)
        return ch

    def redo(self) -> Change | None:
        if not self._redo:
            return None
        ch = self._redo.pop()
        self._restore(ch.path, ch.after)
        self._undo.append(ch)
        return ch

    def history(self) -> list[Change]:
        return list(self._undo)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def snapshot_state(self, name: str) -> None:
        """Save a pointer to the current undo stack under a name."""
        self._snapshots[name] = list(self._undo)

    def rollback_to(self, name: str) -> int:
        """Revert changes back to a named snapshot. Returns number of changes reverted."""
        if name not in self._snapshots:
            raise ValueError(f"Snapshot '{name}' not found.")
        
        target_state = self._snapshots[name]
        reverted_count = 0
        
        # Keep undoing until our undo stack matches the target state
        while len(self._undo) > len(target_state):
            self.undo()
            reverted_count += 1
            
        return reverted_count

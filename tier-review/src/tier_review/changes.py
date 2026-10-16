from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FileStatus(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass(frozen=True)
class ChangeBlock:
    """One run of consecutive removed and/or added lines.

    `new_lines` are in the new version of the file, `old_lines` in the base version.
    A pure deletion has no added lines; it is represented on the new side by the lines
    surrounding the removed block, since that is where behaviour changes.
    """

    new_lines: frozenset[int]
    old_lines: frozenset[int] = frozenset()


@dataclass(frozen=True)
class ChangedFile:
    """A file touched by the change.

    `lines` are line numbers in the *new* version of the file. `blocks` tie them to the
    base lines they replace, when the diff tells us (an untracked file has none).
    """

    path: str
    status: FileStatus = FileStatus.MODIFIED
    lines: frozenset[int] = field(default_factory=frozenset)
    blocks: tuple[ChangeBlock, ...] = ()

    def replaced_lines(self, line: int) -> frozenset[int]:
        """Base lines replaced or removed by the block that produced new-side `line`."""
        return frozenset(old for block in self.blocks if line in block.new_lines for old in block.old_lines)


@dataclass(frozen=True)
class ChangeSet:
    files: tuple[ChangedFile, ...]

    def __iter__(self):
        return iter(self.files)

    def __len__(self):
        return len(self.files)

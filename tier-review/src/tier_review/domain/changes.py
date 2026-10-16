from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FileStatus(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass(frozen=True)
class ChangedFile:
    """A file touched by the change.

    `lines` are line numbers in the *new* version of the file. Pure deletions are
    represented by the lines surrounding the removed block, since that is where
    behaviour changes.
    """

    path: str
    status: FileStatus = FileStatus.MODIFIED
    lines: frozenset[int] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ChangeSet:
    files: tuple[ChangedFile, ...]

    def __iter__(self):
        return iter(self.files)

    def __len__(self):
        return len(self.files)

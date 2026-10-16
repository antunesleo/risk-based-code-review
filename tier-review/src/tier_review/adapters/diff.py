"""DiffSource adapters: parse `git diff -U0` output, from git itself or from text."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from tier_review.domain import ChangedFile, ChangeSet, FileStatus

_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class ProjectScope:
    """Restricts repository paths to one project directory and makes them relative to it."""

    prefix: str = ""

    def relativize(self, repo_path: str) -> str | None:
        prefix = self.prefix.strip("/")
        if not prefix:
            return repo_path
        if repo_path.startswith(prefix + "/"):
            return repo_path[len(prefix) + 1 :]
        return None


def parse_unified_diff(text: str, scope: ProjectScope = ProjectScope()) -> ChangeSet:
    """Parse a git unified diff with any amount of context.

    Changed lines are reported on the new side. A removed block with nothing added
    in its place is attributed to the new lines on both sides of the gap.
    """
    files: list[_FileBuilder] = []
    current: _FileBuilder | None = None
    hunk: _Hunk | None = None
    for raw in text.splitlines():
        if hunk and not hunk.done:
            hunk.feed(raw)
            continue
        if hunk:
            hunk.close()
            hunk = None
        if match := _HEADER.match(raw):
            current = _FileBuilder(path=match.group(2))
            files.append(current)
        elif current is None:
            continue
        elif raw.startswith("new file mode"):
            current.status = FileStatus.ADDED
        elif raw.startswith("deleted file mode"):
            current.status = FileStatus.DELETED
        elif raw.startswith("rename to "):
            current.status = FileStatus.RENAMED
        elif raw.startswith("+++ b/"):
            current.path = raw[len("+++ b/") :]
        elif match := _HUNK.match(raw):
            hunk = _Hunk(current.lines, *(int(g) if g is not None else 1 for g in match.groups()))
    if hunk:
        hunk.close()

    scoped = []
    for changed in files:
        relative = scope.relativize(changed.path)
        if relative is not None:
            scoped.append(ChangedFile(relative, changed.status, frozenset(changed.lines)))
    return ChangeSet(tuple(scoped))


@dataclass
class _FileBuilder:
    path: str
    status: FileStatus = FileStatus.MODIFIED
    lines: set[int] = field(default_factory=set)


class _Hunk:
    def __init__(self, sink: set[int], _old_start: int, old_count: int, new_start: int, new_count: int):
        self._sink = sink
        self._old_left = old_count
        self._new_left = new_count
        # For an empty new side git reports the line *before* the gap.
        self._next_new = new_start if new_count else new_start + 1
        self._pending_deletion = False

    @property
    def done(self) -> bool:
        return self._old_left <= 0 and self._new_left <= 0

    def feed(self, raw: str) -> None:
        marker = raw[:1]
        if marker == "+":
            self._sink.add(self._next_new)
            self._pending_deletion = False
            self._next_new += 1
            self._new_left -= 1
        elif marker == "-":
            self._pending_deletion = True
            self._old_left -= 1
        elif marker == "\\":  # "\ No newline at end of file"
            return
        else:
            self._flush_deletion()
            self._next_new += 1
            self._old_left -= 1
            self._new_left -= 1

    def close(self) -> None:
        self._flush_deletion()

    def _flush_deletion(self) -> None:
        if self._pending_deletion:
            self._sink.update(line for line in (self._next_new - 1, self._next_new) if line > 0)
            self._pending_deletion = False


class TextDiffSource:
    def __init__(self, text: str, scope: ProjectScope = ProjectScope()):
        self._text = text
        self._scope = scope

    def changes(self) -> ChangeSet:
        return parse_unified_diff(self._text, self._scope)


class GitDiffSource:
    """Working tree (plus untracked files) compared against `base`."""

    def __init__(self, repo: Path, base: str, scope: ProjectScope = ProjectScope(), include_untracked: bool = True):
        self._repo = repo
        self._base = base
        self._scope = scope
        self._include_untracked = include_untracked

    def changes(self) -> ChangeSet:
        tracked = parse_unified_diff(
            self._git("diff", "-U0", "--no-color", "--no-ext-diff", "-M", self._base, "--"), self._scope
        )
        if not self._include_untracked:
            return tracked
        return ChangeSet(tracked.files + tuple(self._untracked()))

    def _untracked(self):
        for repo_path in self._git("ls-files", "--others", "--exclude-standard").splitlines():
            relative = self._scope.relativize(repo_path)
            if relative is None:
                continue
            try:
                line_count = len((self._repo / repo_path).read_text(errors="replace").splitlines())
            except OSError:
                line_count = 0
            yield ChangedFile(relative, FileStatus.ADDED, frozenset(range(1, line_count + 1)))

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(self._repo), *args],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout

"""ScopeResolver that finds the innermost enclosing function using the stdlib AST."""
from __future__ import annotations

import ast
from functools import cache
from pathlib import Path

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef)


class AstScopeResolver:
    def __init__(self, project_root: Path):
        self._root = project_root

    def enclosing_scope(self, path: str, line: int) -> range | None:
        innermost = None
        for start, end in self._scopes(path):
            if start <= line <= end and (innermost is None or end - start < innermost[1] - innermost[0]):
                innermost = (start, end)
        return range(innermost[0], innermost[1] + 1) if innermost else None

    @cache
    def _scopes(self, path: str) -> tuple[tuple[int, int], ...]:
        try:
            tree = ast.parse((self._root / path).read_text())
        except (OSError, SyntaxError, ValueError):
            return ()
        return tuple(
            (min([node.lineno, *(d.lineno for d in node.decorator_list)]), node.end_lineno or node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, _SCOPES)
        )

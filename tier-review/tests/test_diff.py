from tier_review.diff import ProjectScope, parse_unified_diff
from tier_review.changes import FileStatus

DIFF = """\
diff --git a/helpdesk/app/sla.py b/helpdesk/app/sla.py
index 1111111..2222222 100644
--- a/helpdesk/app/sla.py
+++ b/helpdesk/app/sla.py
@@ -18 +18 @@ def is_breached(ticket, at=None):
-        return ticket["closed_at"] > ticket["due_at"]
+        return ticket["closed_at"] >= ticket["due_at"]
@@ -30,2 +29,0 @@ def other():
-    a = 1
-    b = 2
diff --git a/helpdesk/app/new.py b/helpdesk/app/new.py
new file mode 100644
--- /dev/null
+++ b/helpdesk/app/new.py
@@ -0,0 +1,3 @@
+x = 1
+y = 2
+z = 3
diff --git a/helpdesk/app/gone.py b/helpdesk/app/gone.py
deleted file mode 100644
--- a/helpdesk/app/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-a
-b
diff --git a/docs/notes.md b/docs/notes.md
--- a/docs/notes.md
+++ b/docs/notes.md
@@ -1 +1 @@
-old
+new
"""


def test_parses_new_side_lines_statuses_and_scopes_to_project():
    files = {f.path: f for f in parse_unified_diff(DIFF, ProjectScope("helpdesk"))}

    assert set(files) == {"app/sla.py", "app/new.py", "app/gone.py"}
    assert files["app/sla.py"].lines == {18, 29, 30}  # 29/30 surround the deleted block
    assert files["app/new.py"].status is FileStatus.ADDED and files["app/new.py"].lines == {1, 2, 3}
    assert files["app/gone.py"].status is FileStatus.DELETED


def test_detects_pure_renames():
    diff = "diff --git a/app/a.py b/app/b.py\nsimilarity index 100%\nrename from app/a.py\nrename to app/b.py\n"

    (renamed,) = parse_unified_diff(diff)

    assert renamed.path == "app/b.py" and renamed.status is FileStatus.RENAMED


def test_context_lines_are_not_reported_as_changes():
    diff = """\
diff --git a/app/x.py b/app/x.py
--- a/app/x.py
+++ b/app/x.py
@@ -1,7 +1,7 @@
 def f():
     a = 1
-    b = 2
+    b = 3
     c = 3
-    d = 4
     e = 5
+    f = 6
     return a
"""
    (changed,) = parse_unified_diff(diff)

    assert changed.lines == {3, 4, 5, 6}  # 3 replaced, 4/5 surround the removed `d`, 6 added
    assert changed.replaced_lines(3) == {3}
    assert changed.replaced_lines(4) == {5} and changed.replaced_lines(5) == {5}
    assert changed.replaced_lines(6) == frozenset()


def test_pure_deletion_keeps_the_removed_base_lines():
    files = {f.path: f for f in parse_unified_diff(DIFF, ProjectScope("helpdesk"))}

    assert files["app/sla.py"].replaced_lines(29) == {30, 31}
    assert files["app/sla.py"].replaced_lines(18) == {18}


def test_blank_lines_are_not_changes():
    diff = """\
diff --git a/app/x.py b/app/x.py
--- a/app/x.py
+++ b/app/x.py
@@ -2,0 +3,4 @@
+
+
+def g():
+    return 1
"""
    (changed,) = parse_unified_diff(diff)

    assert changed.lines == {5, 6}

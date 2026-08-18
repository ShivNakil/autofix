from app.tools.patching import extract_patch, validate_patch


def test_extract_patch():
    text = """Here is the patch:

```diff
diff --git a/example.py b/example.py
--- a/example.py
+++ b/example.py
@@ -1 +1 @@
-x = 1
+x = 2
```
"""
    patch = extract_patch(text)
    validate_patch(patch)

    assert "x = 2" in patch


def test_reject_empty_patch():
    import pytest

    with pytest.raises(ValueError):
        validate_patch("")

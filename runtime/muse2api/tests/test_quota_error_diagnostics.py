"""Quota diagnostics must not turn generic prompt/model limits into account exhaustion."""
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "engine.py").read_text(encoding="utf-8"))
engine = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MuseEngine")
method = next(node for node in engine.body
              if isinstance(node, ast.FunctionDef) and node.name == "_quota_limit_diagnostic")
module = ast.Module(body=[
    ast.ClassDef(name="Diagnostic", bases=[], keywords=[], body=[method], decorator_list=[])
], type_ignores=[])
scope = {"re": re}
exec(compile(ast.fix_missing_locations(module), str(ROOT / "engine.py"), "exec"), scope)
diagnose = scope["Diagnostic"]._quota_limit_diagnostic

assert "Account quota exhausted" in diagnose("Muse says: Account quota exhausted")
assert "额度不足" in diagnose("账号额度不足")
assert "out of credits" in diagnose("Generation failed: out of credits")
assert diagnose("The prompt exceeds the token limit; shorten the prompt") == ""
assert diagnose("The video reached its maximum duration limit: 6 seconds") == ""
assert diagnose("Free plan, 8% used; additional 2B tokens left") == ""
assert "[redacted]" in diagnose("Account quota exhausted; Bearer secret-marker")

print("PASS: explicit quota diagnostics; generic token/duration limits are not mislabeled")

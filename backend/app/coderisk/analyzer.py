"""
DevTwin CodeRisk — Static Analysis Engine

Executes deterministic, non-executing static analysis checks against
mined code trees and AST representations. Never imports or executes repository code.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.coderisk.models import CodeRiskFinding
from app.coderisk.rules import RULES
from app.mining.models import MiningResult

# Maximum resource budgets for static analysis
MAX_SOURCE_FILES_INSPECTED = 500
MAX_SINGLE_FILE_BYTES = 512 * 1024  # 512 KB

EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "target",
    "vendor",
}

# Regex pattern for hardcoded secrets
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"""(?i)\b(?:api_key|secret_key|private_key|auth_token|aws_secret_access_key|access_token|db_password|password)\b\s*[:=]\s*["']([^"'\s]{16,})["']"""
)

KNOWN_PLACEHOLDERS = {
    "your_api_key_here",
    "your-api-key-here",
    "your_secret_here",
    "your-secret-here",
    "insert_secret_here",
    "insert-secret-here",
    "changeme",
    "placeholder",
    "example",
    "dummy",
    "test",
    "xxxxxxxxxxxxxxxx",
    "0000000000000000",
}


def _is_obvious_placeholder(val: str) -> bool:
    """Returns True if the string literal is an obvious template placeholder."""
    v_lower = val.lower().strip()
    if v_lower in KNOWN_PLACEHOLDERS:
        return True
    if v_lower.startswith(("your_", "your-", "insert_", "insert-", "placeholder", "dummy", "my_secret", "my-secret")):
        return True
    if len(set(v_lower)) <= 3:  # Low entropy repeated characters like 'aaaaa...'
        return True
    return False


class PythonRiskASTVisitor(ast.NodeVisitor):
    """
    Standard-library AST visitor inspecting code constructs without executing source.
    """

    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.findings: List[CodeRiskFinding] = []
        self._imported_modules: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._imported_modules.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self._imported_modules.add(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # SEC-002: eval() or exec()
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            rule = RULES["SEC-002"]
            self.findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation=f"Direct call to dynamic execution construct '{node.func.id}()'.",
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    evidence_snippet=f"{node.func.id}(...)",
                )
            )

        # SEC-002: os.system()
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "system"
        ):
            rule = RULES["SEC-002"]
            self.findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation="Direct shell execution via 'os.system()' construct.",
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    evidence_snippet="os.system(...)",
                )
            )

        # SEC-003: pickle.load or pickle.loads
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pickle"
            and node.func.attr in ("load", "loads")
        ):
            rule = RULES["SEC-003"]
            self.findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation=f"Untrusted object deserialization via 'pickle.{node.func.attr}()'.",
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    evidence_snippet=f"pickle.{node.func.attr}(...)",
                )
            )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # REL-001: Bare except:
        if node.type is None:
            rule = RULES["REL-001"]
            self.findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation="Bare 'except:' handler catches BaseException and masks system exit signals.",
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    evidence_snippet="except:",
                )
            )

        # REL-002: Empty pass in exception handler
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            rule = RULES["REL-002"]
            self.findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation="Exception handler contains only 'pass', silently swallowing potential failures.",
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    evidence_snippet="except ...: pass",
                )
            )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_param_count(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_param_count(node)
        self.generic_visit(node)

    def _check_param_count(self, node):
        # MAINT-001: Excessive parameters (> 7)
        total_args = (
            len(node.args.args)
            + len(getattr(node.args, "posonlyargs", []))
            + len(node.args.kwonlyargs)
        )
        if total_args > 7:
            rule = RULES["MAINT-001"]
            self.findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation=f"Function '{node.name}' defines {total_args} parameters (threshold: 7).",
                    file_path=self.rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    evidence_snippet=f"def {node.name}(...)",
                )
            )


def analyze_repository_risks(
    root_dir: Optional[Path],
    mining_result: MiningResult,
) -> List[CodeRiskFinding]:
    """
    Performs deterministic, bounded static risk analysis on repository contents and mining data.
    Never executes code, imports untrusted modules, or spawns subprocesses.
    """
    findings: List[CodeRiskFinding] = []
    seen_dedup_keys: Set[Tuple[str, Optional[str], Optional[int]]] = set()

    # -----------------------------------------------------------------------
    # 1. Syntactic Parse Failures (MAINT-002) from Mining Result
    # -----------------------------------------------------------------------
    for ast_file in mining_result.ast_summaries:
        if ast_file.parse_error:
            rule = RULES["MAINT-002"]
            findings.append(
                CodeRiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    severity=rule.severity,
                    confidence=rule.confidence,
                    title=rule.title,
                    explanation=f"Syntax parse failure: {ast_file.parse_error}",
                    file_path=ast_file.file_path,
                    line_start=1,
                    line_end=1,
                    evidence_snippet=ast_file.parse_error[:80],
                )
            )

    # -----------------------------------------------------------------------
    # 2. Testing Coverage Heuristic (TEST-001)
    # -----------------------------------------------------------------------
    has_test_evidence = False
    for ast_file in mining_result.ast_summaries:
        lower_p = ast_file.file_path.lower()
        if "test_" in lower_p or "_test.py" in lower_p or "tests/" in lower_p or "test/" in lower_p:
            has_test_evidence = True
            break

    if not has_test_evidence:
        for manifest in mining_result.manifests:
            for dep in manifest.dependencies:
                if dep.name.lower() in ("pytest", "jest", "unittest", "mocha", "vitest"):
                    has_test_evidence = True
                    break

    # If substantial source files exist but zero tests are detected
    if not has_test_evidence and mining_result.inventory.source_files >= 5:
        rule = RULES["TEST-001"]
        findings.append(
            CodeRiskFinding(
                rule_id=rule.rule_id,
                category=rule.category,
                severity=rule.severity,
                confidence=rule.confidence,
                title=rule.title,
                explanation="Repository contains 5 or more source files but no test files or testing frameworks were detected.",
                file_path=None,
                line_start=None,
                line_end=None,
                evidence_snippet=f"{mining_result.inventory.source_files} source files without test files",
            )
        )

    # -----------------------------------------------------------------------
    # 3. Source File AST & Secret Inspections (when workspace is present)
    # -----------------------------------------------------------------------
    if root_dir and root_dir.exists() and root_dir.is_dir():
        files_inspected = 0
        resolved_root = root_dir.resolve()

        for dirpath, dirnames, filenames in os.walk(resolved_root):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]

            for fname in filenames:
                if files_inspected >= MAX_SOURCE_FILES_INSPECTED:
                    break

                file_path = Path(dirpath) / fname
                try:
                    if not file_path.is_file() or file_path.is_symlink():
                        continue

                    size = file_path.stat().st_size
                    if size > MAX_SINGLE_FILE_BYTES or size == 0:
                        continue

                    rel_path = str(file_path.relative_to(resolved_root)).replace("\\", "/")
                    files_inspected += 1

                    # Read safely in binary mode
                    with open(file_path, "rb") as f:
                        raw_bytes = f.read()

                    # Check for secrets (SEC-001) in text files
                    if b"\x00" not in raw_bytes[:8192]:  # Skip binary files
                        text_content = raw_bytes.decode("utf-8", errors="replace")
                        lines = text_content.splitlines()

                        for line_idx, line_str in enumerate(lines, start=1):
                            match = SECRET_ASSIGNMENT_PATTERN.search(line_str)
                            if match:
                                secret_candidate = match.group(1)
                                if not _is_obvious_placeholder(secret_candidate):
                                    rule = RULES["SEC-001"]
                                    # Never include the actual secret in the snippet!
                                    var_part = line_str.split("=")[0].split(":")[0].strip()
                                    redacted_snippet = f'{var_part} = "[REDACTED_SECRET]"'[:80]
                                    findings.append(
                                        CodeRiskFinding(
                                            rule_id=rule.rule_id,
                                            category=rule.category,
                                            severity=rule.severity,
                                            confidence=rule.confidence,
                                            title=rule.title,
                                            explanation="Potential high-entropy secret, token, or API key assignment detected.",
                                            file_path=rel_path,
                                            line_start=line_idx,
                                            line_end=line_idx,
                                            evidence_snippet=redacted_snippet,
                                        )
                                    )

                        # Run Python AST visitor on .py files
                        if fname.endswith(".py"):
                            try:
                                tree = ast.parse(text_content, filename=rel_path)
                                visitor = PythonRiskASTVisitor(rel_path=rel_path)
                                visitor.visit(tree)
                                findings.extend(visitor.findings)
                            except (SyntaxError, RecursionError):
                                pass  # Parse errors already captured by MAINT-002

                except Exception:
                    continue  # Ignore inaccessible/unreadable files safely

    # -----------------------------------------------------------------------
    # 4. Deduplicate & Sort Findings Deterministically
    # -----------------------------------------------------------------------
    unique_findings: List[CodeRiskFinding] = []
    for f in findings:
        key = (f.rule_id, f.file_path, f.line_start)
        if key not in seen_dedup_keys:
            seen_dedup_keys.add(key)
            unique_findings.append(f)

    # Sort deterministically
    unique_findings.sort(key=lambda x: (x.file_path or "", x.line_start or 0, x.rule_id))
    return unique_findings

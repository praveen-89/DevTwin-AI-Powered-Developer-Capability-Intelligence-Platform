"""
DevTwin Mining Engine — AST Parser Foundation
Provides an extensible parser interface with a secure, standard-library Python AST parser.
"""

import abc
import ast
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from app.mining.constants import MAX_SINGLE_SOURCE_FILE_BYTES
from app.mining.models import (
    ASTClassSummary,
    ASTFileSummary,
    ASTFunctionSummary,
    ASTImportSummary,
    MiningWarning,
)

logger = logging.getLogger(__name__)


class BaseASTParser(abc.ABC):
    """
    Abstract interface for source code AST parsers.
    Parsers MUST NOT execute untrusted source code.
    """

    @abc.abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Determines if this parser handles the given file."""
        pass

    @abc.abstractmethod
    def parse_file(
        self,
        file_path: Path,
        rel_path: str,
        source_bytes: bytes,
    ) -> Tuple[Optional[ASTFileSummary], List[MiningWarning]]:
        """Parses the source bytes into an ASTFileSummary."""
        pass


class PythonASTParser(BaseASTParser):
    """
    Standard library-based Python AST parser.
    Extracts functions, classes, imports, and docstring presence safely.
    """

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".py", ".pyi")

    def parse_file(
        self,
        file_path: Path,
        rel_path: str,
        source_bytes: bytes,
    ) -> Tuple[Optional[ASTFileSummary], List[MiningWarning]]:
        warnings: List[MiningWarning] = []

        if len(source_bytes) > MAX_SINGLE_SOURCE_FILE_BYTES:
            warnings.append(
                MiningWarning(
                    file_path=rel_path,
                    warning_code="AST_SOURCE_OVERSIZED",
                    message=f"Python source exceeds AST parse size budget ({len(source_bytes)} > {MAX_SINGLE_SOURCE_FILE_BYTES} bytes).",
                )
            )
            return None, warnings

        # Safe decoding
        try:
            source_text = source_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                source_text = source_bytes.decode("latin-1")
            except Exception as e:
                warnings.append(
                    MiningWarning(
                        file_path=rel_path,
                        warning_code="AST_DECODE_ERROR",
                        message=f"Failed to decode Python source: {type(e).__name__}.",
                    )
                )
                return None, warnings

        try:
            tree = ast.parse(source_text, filename=rel_path)
        except (SyntaxError, IndentationError) as exc:
            line_no = exc.lineno or 0
            warnings.append(
                MiningWarning(
                    file_path=rel_path,
                    warning_code="AST_SYNTAX_ERROR",
                    message=f"Python syntax error at line {line_no}.",
                )
            )
            return (
                ASTFileSummary(
                    file_path=rel_path,
                    language="Python",
                    functions_count=0,
                    classes_count=0,
                    imports_count=0,
                    parse_error=f"SYNTAX_ERROR:line_{line_no}",
                ),
                warnings,
            )
        except (RecursionError, MemoryError, ValueError) as exc:
            warnings.append(
                MiningWarning(
                    file_path=rel_path,
                    warning_code="AST_PARSE_LIMIT",
                    message=f"AST parsing aborted due to resource limitation: {type(exc).__name__}.",
                )
            )
            return (
                ASTFileSummary(
                    file_path=rel_path,
                    language="Python",
                    functions_count=0,
                    classes_count=0,
                    imports_count=0,
                    parse_error=type(exc).__name__,
                ),
                warnings,
            )

        functions: List[ASTFunctionSummary] = []
        classes: List[ASTClassSummary] = []
        imports: List[ASTImportSummary] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_doc = (
                    bool(ast.get_docstring(node))
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    else False
                )
                args_count = len(node.args.args)
                functions.append(
                    ASTFunctionSummary(
                        name=node.name,
                        line_number=node.lineno,
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        args_count=args_count,
                        has_docstring=has_doc,
                    )
                )

            elif isinstance(node, ast.ClassDef):
                has_doc = bool(ast.get_docstring(node))
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)
                # Count inner methods
                method_count = sum(
                    1 for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                classes.append(
                    ASTClassSummary(
                        name=node.name,
                        line_number=node.lineno,
                        base_classes=base_names,
                        methods_count=method_count,
                        has_docstring=has_doc,
                    )
                )

            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                imports.append(
                    ASTImportSummary(
                        module=None,
                        names=names,
                        is_from=False,
                        line_number=node.lineno,
                    )
                )

            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                imports.append(
                    ASTImportSummary(
                        module=node.module,
                        names=names,
                        is_from=True,
                        line_number=node.lineno,
                    )
                )

        # Sort deterministically by line number
        functions.sort(key=lambda f: f.line_number)
        classes.sort(key=lambda c: c.line_number)
        imports.sort(key=lambda i: i.line_number)

        summary = ASTFileSummary(
            file_path=rel_path,
            language="Python",
            functions_count=len(functions),
            classes_count=len(classes),
            imports_count=len(imports),
            functions=functions,
            classes=classes,
            imports=imports,
        )
        return summary, warnings

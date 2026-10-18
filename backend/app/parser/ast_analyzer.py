"""
CodeGraph AI - AST Static Analyzer
Extracts files, classes, functions, calls, imports, and inheritance
using Python's built-in `ast` module without executing any code.
"""

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class FileNode:
    """Represents a source file in the repository."""
    id: str  # "file:path/to/file.py"
    path: str  # Repository-relative normalized path
    name: str  # Base filename
    line_count: int


@dataclass
class ClassNode:
    """Represents a class definition."""
    id: str  # "class:path/to/file.py:ClassName"
    name: str
    file_path: str
    start_line: int
    end_line: int
    base_classes: List[str] = field(default_factory=list)


@dataclass
class FunctionNode:
    """Represents a function or method definition."""
    id: str  # "func:path/to/file.py:scope:name:start_line"
    name: str
    file_path: str
    scope: str  # "global" or class name
    start_line: int
    end_line: int
    is_method: bool
    args: List[str] = field(default_factory=list)


@dataclass
class ImportEdge:
    """Represents an import statement connecting files or modules."""
    id: str
    source_file: str
    imported_module: str
    imported_name: Optional[str] = None
    alias: Optional[str] = None
    line_number: int = 1
    resolved_file: Optional[str] = None


@dataclass
class InheritanceEdge:
    """Represents a subclass-to-superclass relationship."""
    id: str
    subclass_id: str
    subclass_name: str
    superclass_name: str
    file_path: str
    resolved_superclass_id: Optional[str] = None


@dataclass
class CallEdge:
    """Represents a function call invocation."""
    id: str
    caller_id: str
    caller_name: str
    caller_file: str
    callee_name: str
    line_number: int
    callee_object: Optional[str] = None  # e.g., "self", "logger", "rule"
    resolved_callee_id: Optional[str] = None
    is_resolved: bool = False
    unresolved_reason: Optional[str] = None


@dataclass
class AnalysisResult:
    """Structured container holding all verified entities and relationships."""
    repo_root: str
    files: List[FileNode] = field(default_factory=list)
    classes: List[ClassNode] = field(default_factory=list)
    functions: List[FunctionNode] = field(default_factory=list)
    calls: List[CallEdge] = field(default_factory=list)
    imports: List[ImportEdge] = field(default_factory=list)
    inheritances: List[InheritanceEdge] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def get_unused_functions(self) -> List[FunctionNode]:
        """
        Identify functions with zero incoming resolved calls.
        Excludes constructors, dunder methods, and tests.
        """
        called_function_ids: Set[str] = {
            call.resolved_callee_id
            for call in self.calls
            if call.is_resolved and call.resolved_callee_id
        }

        unused: List[FunctionNode] = []
        for func in self.functions:
            if func.name.startswith("__") and func.name.endswith("__"):
                continue
            if func.name.startswith("test_"):
                continue
            if func.id not in called_function_ids:
                unused.append(func)

        return unused

    def summary(self) -> Dict[str, Any]:
        """Return a statistical overview of the analyzed codebase."""
        resolved_calls = sum(1 for c in self.calls if c.is_resolved)
        return {
            "total_files": len(self.files),
            "total_classes": len(self.classes),
            "total_functions": len(self.functions),
            "total_calls": len(self.calls),
            "resolved_calls": resolved_calls,
            "unresolved_calls": len(self.calls) - resolved_calls,
            "total_imports": len(self.imports),
            "total_inheritances": len(self.inheritances),
            "unused_functions": len(self.get_unused_functions()),
            "errors": len(self.errors),
        }


class _ASTCollector(ast.NodeVisitor):
    """Internal AST visitor collecting raw entities from a single Python file."""

    def __init__(self, rel_path: str):
        self.rel_path = rel_path
        self.classes: List[ClassNode] = []
        self.functions: List[FunctionNode] = []
        self.imports: List[ImportEdge] = []
        self.raw_calls: List[Dict[str, Any]] = []

        self._current_class: Optional[str] = None
        self._current_function: Optional[FunctionNode] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            edge = ImportEdge(
                id=f"import:{self.rel_path}:{node.lineno}:{alias.name}",
                source_file=self.rel_path,
                imported_module=alias.name,
                alias=alias.asname,
                line_number=node.lineno,
            )
            self.imports.append(edge)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        # Handle relative imports e.g., 'from . import foo'
        prefix = "." * node.level
        full_module = f"{prefix}{module}" if prefix else module

        for alias in node.names:
            edge = ImportEdge(
                id=f"import:{self.rel_path}:{node.lineno}:{full_module}:{alias.name}",
                source_file=self.rel_path,
                imported_module=full_module,
                imported_name=alias.name,
                alias=alias.asname,
                line_number=node.lineno,
            )
            self.imports.append(edge)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        bases: List[str] = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(f"{self._extract_attr_chain(b)}")

        class_id = f"class:{self.rel_path}:{node.name}"
        class_node = ClassNode(
            id=class_id,
            name=node.name,
            file_path=self.rel_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            base_classes=bases,
        )
        self.classes.append(class_node)

        prev_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node)

    def _process_function(self, node: Any):
        is_method = self._current_class is not None
        scope = self._current_class if is_method else "global"
        func_id = f"func:{self.rel_path}:{scope}:{node.name}:{node.lineno}"

        args = [arg.arg for arg in node.args.args]

        func_node = FunctionNode(
            id=func_id,
            name=node.name,
            file_path=self.rel_path,
            scope=scope,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            is_method=is_method,
            args=args,
        )
        self.functions.append(func_node)

        prev_func = self._current_function
        self._current_function = func_node
        self.generic_visit(node)
        self._current_function = prev_func

    def visit_Call(self, node: ast.Call):
        callee_name = ""
        callee_object = None

        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                callee_object = node.func.value.id
            elif isinstance(node.func.value, ast.Attribute):
                callee_object = self._extract_attr_chain(node.func.value)

        if callee_name:
            caller_id = (
                self._current_function.id
                if self._current_function
                else f"file:{self.rel_path}"
            )
            caller_name = (
                self._current_function.name
                if self._current_function
                else f"<module:{self.rel_path}>"
            )

            self.raw_calls.append(
                {
                    "caller_id": caller_id,
                    "caller_name": caller_name,
                    "caller_file": self.rel_path,
                    "callee_name": callee_name,
                    "callee_object": callee_object,
                    "line_number": node.lineno,
                }
            )

        self.generic_visit(node)

    def _extract_attr_chain(self, node: ast.Attribute) -> str:
        parts = [node.attr]
        curr = node.value
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            parts.append(curr.id)
        return ".".join(reversed(parts))


class ASTAnalyzer:
    """
    Analyzes Python repositories using pure AST static analysis.
    Safely discovers files, classes, functions, calls, and imports.
    """

    IGNORED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".idea",
        ".vscode",
        ".mypy_cache",
        "dist",
        "build",
    }

    BUILTIN_FUNCTIONS = {
        "print", "len", "sum", "min", "max", "range", "enumerate", "isinstance",
        "issubclass", "open", "abs", "round", "zip", "map", "filter", "any", "all",
        "int", "float", "str", "bool", "list", "dict", "set", "tuple", "super",
        "getattr", "setattr", "hasattr", "repr", "type", "id", "format",
    }

    def __init__(self, max_file_size_bytes: int = 1024 * 1024):
        self.max_file_size_bytes = max_file_size_bytes

    def analyze_repository(self, repo_path: str) -> AnalysisResult:
        """
        Scan a local directory and build a complete static graph of entities.
        Raises ValueError if path traversal or invalid paths are detected.
        """
        resolved_root = Path(repo_path).resolve()
        if not resolved_root.exists() or not resolved_root.is_dir():
            raise ValueError(f"Repository path does not exist or is not a directory: {repo_path}")

        result = AnalysisResult(repo_root=str(resolved_root))

        # 1. Discover all Python files safely
        discovered_files: List[Path] = []
        for root, dirs, files in os.walk(resolved_root):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS and not d.startswith(".")]

            for file in files:
                if file.endswith(".py"):
                    full_file_path = Path(root) / file
                    # Path boundary verification
                    try:
                        resolved_file = full_file_path.resolve()
                        resolved_file.relative_to(resolved_root)
                        discovered_files.append(resolved_file)
                    except ValueError:
                        result.errors.append({
                            "type": "SecurityViolation",
                            "message": f"File escaped repository root: {full_file_path}",
                        })

        raw_calls_all: List[Dict[str, Any]] = []

        # 2. Extract entities file by file
        for file_path in discovered_files:
            rel_path = str(file_path.relative_to(resolved_root)).replace("\\", "/")

            try:
                stat = file_path.stat()
                if stat.st_size > self.max_file_size_bytes:
                    result.errors.append({
                        "file": rel_path,
                        "type": "FileTooLarge",
                        "message": f"File size {stat.st_size} exceeds limit {self.max_file_size_bytes}",
                    })
                    continue

                content = file_path.read_text(encoding="utf-8", errors="replace")
                line_count = len(content.splitlines())

                tree = ast.parse(content, filename=rel_path)

                collector = _ASTCollector(rel_path)
                collector.visit(tree)

                result.files.append(
                    FileNode(
                        id=f"file:{rel_path}",
                        path=rel_path,
                        name=file_path.name,
                        line_count=line_count,
                    )
                )
                result.classes.extend(collector.classes)
                result.functions.extend(collector.functions)
                result.imports.extend(collector.imports)
                raw_calls_all.extend(collector.raw_calls)

            except SyntaxError as syn_err:
                result.errors.append({
                    "file": rel_path,
                    "type": "SyntaxError",
                    "line": syn_err.lineno,
                    "message": str(syn_err),
                })
            except Exception as exc:
                result.errors.append({
                    "file": rel_path,
                    "type": "ScanError",
                    "message": str(exc),
                })

        # 3. Build Symbol Tables for Resolution
        self._resolve_relationships(result, raw_calls_all)

        return result

    def _resolve_relationships(self, result: AnalysisResult, raw_calls: List[Dict[str, Any]]):
        """Cross-reference symbols across the repository to resolve calls, imports, and inheritance."""
        # Index files by relative path without extension (e.g., 'utils/logger' or 'services.order_service')
        file_map: Dict[str, str] = {}
        for f in result.files:
            file_map[f.path] = f.path
            base_module = f.path[:-3] if f.path.endswith(".py") else f.path
            file_map[base_module.replace("/", ".")] = f.path
            file_map[base_module] = f.path

        # Index classes: (file_path, class_name) -> ClassNode and class_name -> list[ClassNode]
        class_by_file_and_name: Dict[Tuple[str, str], ClassNode] = {}
        class_by_name: Dict[str, List[ClassNode]] = {}
        for c in result.classes:
            class_by_file_and_name[(c.file_path, c.name)] = c
            class_by_name.setdefault(c.name, []).append(c)

        # Index functions: (file_path, scope, func_name) -> FunctionNode
        func_by_file_scope_name: Dict[Tuple[str, str, str], FunctionNode] = {}
        func_by_file_and_name: Dict[Tuple[str, str], List[FunctionNode]] = {}
        for f in result.functions:
            func_by_file_scope_name[(f.file_path, f.scope, f.name)] = f
            func_by_file_and_name.setdefault((f.file_path, f.name), []).append(f)

        # Index imports per file: file_path -> { imported_symbol_or_module: (target_module, target_name) }
        imports_by_file: Dict[str, Dict[str, ImportEdge]] = {}
        for imp in result.imports:
            # Resolve imported file path
            mod_clean = imp.imported_module.lstrip(".")
            resolved_target = file_map.get(mod_clean) or file_map.get(mod_clean.replace(".", "/"))
            if not resolved_target:
                # Check if it corresponds to a folder package e.g. 'services'
                init_candidate = f"{mod_clean.replace('.', '/')}/__init__.py"
                resolved_target = file_map.get(init_candidate)

            imp.resolved_file = resolved_target

            file_imports = imports_by_file.setdefault(imp.source_file, {})
            # If alias is used, bind alias; otherwise bind imported_name or module name
            bind_name = imp.alias or imp.imported_name or imp.imported_module.split(".")[-1]
            file_imports[bind_name] = imp

        # Resolve Class Inheritance
        for c in result.classes:
            for base_name in c.base_classes:
                edge_id = f"inherits:{c.id}:{base_name}"
                resolved_super_id: Optional[str] = None

                # Check same file first
                if (c.file_path, base_name) in class_by_file_and_name:
                    resolved_super_id = class_by_file_and_name[(c.file_path, base_name)].id
                elif base_name in class_by_name and len(class_by_name[base_name]) == 1:
                    resolved_super_id = class_by_name[base_name][0].id

                result.inheritances.append(
                    InheritanceEdge(
                        id=edge_id,
                        subclass_id=c.id,
                        subclass_name=c.name,
                        superclass_name=base_name,
                        file_path=c.file_path,
                        resolved_superclass_id=resolved_super_id,
                    )
                )

        # Resolve Function Calls
        call_index = 0
        for rc in raw_calls:
            call_index += 1
            caller_file = rc["caller_file"]
            caller_id = rc["caller_id"]
            caller_name = rc["caller_name"]
            callee_name = rc["callee_name"]
            callee_object = rc["callee_object"]
            lineno = rc["line_number"]

            edge_id = f"call:{caller_file}:{lineno}:{callee_name}:{call_index}"
            resolved_id: Optional[str] = None
            unresolved_reason: Optional[str] = None

            # Skip standard Python builtins safely
            if not callee_object and callee_name in self.BUILTIN_FUNCTIONS:
                result.calls.append(
                    CallEdge(
                        id=edge_id,
                        caller_id=caller_id,
                        caller_name=caller_name,
                        caller_file=caller_file,
                        callee_name=callee_name,
                        line_number=lineno,
                        callee_object=callee_object,
                        is_resolved=False,
                        unresolved_reason="builtin_function",
                    )
                )
                continue

            # Case 1: `self.method()` inside a class
            if callee_object == "self":
                # Look up caller function to find its class
                caller_func = next((f for f in result.functions if f.id == caller_id), None)
                if caller_func and caller_func.is_method:
                    class_name = caller_func.scope
                    if (caller_file, class_name, callee_name) in func_by_file_scope_name:
                        resolved_id = func_by_file_scope_name[(caller_file, class_name, callee_name)].id
                    else:
                        # Check inherited methods in base classes
                        parent_class = class_by_file_and_name.get((caller_file, class_name))
                        if parent_class:
                            for base in parent_class.base_classes:
                                if (caller_file, base, callee_name) in func_by_file_scope_name:
                                    resolved_id = func_by_file_scope_name[(caller_file, base, callee_name)].id
                                    break

                if not resolved_id:
                    unresolved_reason = "unresolved_self_method"

            # Case 2: Direct call `func()` without object
            elif not callee_object:
                # 2A: Same-file top-level function
                if (caller_file, "global", callee_name) in func_by_file_scope_name:
                    resolved_id = func_by_file_scope_name[(caller_file, "global", callee_name)].id
                else:
                    # 2B: Explicitly imported function
                    file_imports = imports_by_file.get(caller_file, {})
                    if callee_name in file_imports:
                        imp = file_imports[callee_name]
                        if imp.resolved_file:
                            target_file = imp.resolved_file
                            target_name = imp.imported_name or callee_name
                            if (target_file, "global", target_name) in func_by_file_scope_name:
                                resolved_id = func_by_file_scope_name[(target_file, "global", target_name)].id
                            elif (target_file, target_name) in class_by_file_and_name:
                                # Instantiating a class e.g. service = OrderService()
                                target_class = class_by_file_and_name[(target_file, target_name)]
                                resolved_id = target_class.id

                    if not resolved_id:
                        unresolved_reason = "unresolved_symbol_or_external"

            # Case 3: Qualified call `module_or_obj.method()`
            elif callee_object:
                file_imports = imports_by_file.get(caller_file, {})
                if callee_object in file_imports:
                    imp = file_imports[callee_object]
                    if imp.resolved_file:
                        target_file = imp.resolved_file
                        if (target_file, "global", callee_name) in func_by_file_scope_name:
                            resolved_id = func_by_file_scope_name[(target_file, "global", callee_name)].id

                if not resolved_id:
                    unresolved_reason = "dynamic_or_external_receiver"

            result.calls.append(
                CallEdge(
                    id=edge_id,
                    caller_id=caller_id,
                    caller_name=caller_name,
                    caller_file=caller_file,
                    callee_name=callee_name,
                    line_number=lineno,
                    callee_object=callee_object,
                    resolved_callee_id=resolved_id,
                    is_resolved=resolved_id is not None,
                    unresolved_reason=unresolved_reason,
                )
            )

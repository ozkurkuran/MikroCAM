"""Static architecture checks; intentionally independent of application imports."""

import ast
from importlib.util import resolve_name
from pathlib import Path
import sys


CORE_LIBRARIES = {'numpy', 'shapely'}
DISPLAY_LIBRARIES = {'PyQt6', 'PyQt5', 'PySide6', 'PySide2', 'qtpy', 'vispy'}
HARDWARE_STDLIB = {'socket', 'subprocess', 'ctypes', 'multiprocessing'}
ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOTS = {
    path.stem for path in ROOT.glob('*.py')
} | {
    path.name for path in ROOT.iterdir()
    if path.is_dir() and path.name not in {'mikrocam', 'tests'}
    and (any(path.glob('*.py')) or path.name == 'libs')
}


def boundary_reason(source: str, target: str) -> str | None:
    """Return the violated rule, allowing same-layer and inward dependencies."""
    source_parts, target_parts = source.split('.'), target.split('.')
    layer = source_parts[1] if len(source_parts) > 1 else 'root'
    root = target_parts[0]
    if root == 'mikrocam':
        destination = target_parts[1] if len(target_parts) > 1 else 'root'
        if destination == 'root':
            return None  # The package root is checked separately and stays inert.
        if layer == 'ui' or destination == layer:
            return None
        if layer == 'bridge' and destination != 'ui':
            return None
        if layer not in {'root', 'core'} and destination == 'core':
            return None
        return f'{layer} cannot depend on {destination}'
    if root in LEGACY_ROOTS and layer != 'bridge':
        return 'only bridge may import the legacy host'
    if root in DISPLAY_LIBRARIES and layer != 'ui':
        return 'display dependencies belong in ui'
    if layer == 'root' and root not in sys.stdlib_module_names:
        return 'package root must remain stdlib-only'
    if layer not in {'root', 'core', 'bridge', 'ui'} and root not in sys.stdlib_module_names:
        return 'domain dependencies must go through core; only stdlib is directly allowed'
    if layer == 'core':
        if root in HARDWARE_STDLIB:
            return 'core cannot access hardware or processes'
        if root not in sys.stdlib_module_names | CORE_LIBRARIES:
            return 'core permits only stdlib, NumPy and Shapely'
    return None


def _resolve_from(node: ast.ImportFrom, package: str) -> str:
    name = '.' * node.level + (node.module or '')
    return resolve_name(name, package) if node.level else name


def _dynamic_aliases(tree: ast.AST) -> dict[str, str]:
    aliases = {'__import__': 'builtin'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name in {'importlib', 'builtins'}:
                    prefix = item.asname or item.name
                    method = 'import_module' if item.name == 'importlib' else '__import__'
                    aliases[f'{prefix}.{method}'] = 'module' if item.name == 'importlib' else 'builtin'
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                if (node.module, item.name) in {
                    ('importlib', 'import_module'), ('builtins', '__import__'),
                }:
                    aliases[item.asname or item.name] = 'module' if node.module == 'importlib' else 'builtin'
    return aliases


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f'{_call_name(node.value)}.{node.attr}'
    return ''


def _literal_argument(call: ast.Call, position: int, keyword: str) -> str | None:
    value = call.args[position] if len(call.args) > position else next(
        (item.value for item in call.keywords if item.arg == keyword), None)
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


def _dynamic_target(call: ast.Call, kind: str) -> str:
    target = _literal_argument(call, 0, 'name')
    if target is None:
        raise ValueError('unresolved dynamic import target')
    if kind == 'module' and target.startswith('.'):
        package = _literal_argument(call, 1, 'package')
        if package is None:
            raise ValueError('unresolved dynamic import package')
        return resolve_name(target, package)
    if kind == 'builtin':
        level = call.args[4] if len(call.args) > 4 else next(
            (item.value for item in call.keywords if item.arg == 'level'), None)
        if level is not None and not (isinstance(level, ast.Constant) and level.value == 0):
            raise ValueError('relative dynamic __import__ is not supported; use a static import')
    return target


def _dynamic_targets(call: ast.Call, kind: str) -> list[str]:
    target = _dynamic_target(call, kind)
    targets = [target]
    if kind != 'builtin':
        return targets
    fromlist = call.args[3] if len(call.args) > 3 else next(
        (item.value for item in call.keywords if item.arg == 'fromlist'), None)
    if fromlist is None:
        return targets
    if not isinstance(fromlist, (ast.Tuple, ast.List)):
        raise ValueError('unresolved dynamic import fromlist')
    for item in fromlist.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            raise ValueError('unresolved dynamic import fromlist entry')
        if item.value != '*':
            targets.append(f'{target}.{item.value}')
    return targets


def check_source(source: str, module: str, *, is_package: bool = False) -> list[str]:
    """Check static and conventional dynamic imports without executing source."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f'{module}:{exc.lineno}: syntax error: {exc.msg}']
    package = module if is_package else module.rpartition('.')[0]
    aliases = _dynamic_aliases(tree)
    errors = []
    for node in ast.walk(tree):
        targets = []
        try:
            if isinstance(node, ast.Import):
                targets = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                parent = _resolve_from(node, package)
                targets = [parent] + [f'{parent}.{item.name}' for item in node.names if item.name != '*']
            elif isinstance(node, ast.Call) and _call_name(node.func) in aliases:
                targets = _dynamic_targets(node, aliases[_call_name(node.func)])
        except (ValueError, ImportError) as exc:
            errors.append(f'{module}:{node.lineno}: relative/dynamic import: {exc}')
        for target in targets:
            reason = boundary_reason(module, target)
            if reason:
                errors.append(f'{module}:{node.lineno}: {target}: {reason}')
    return errors


def scan_package(package: Path) -> list[str]:
    """Return path-qualified diagnostics for every Python file in a package."""
    errors = []
    for path in sorted(package.rglob('*.py')):
        parts = list(path.relative_to(package.parent).with_suffix('').parts)
        is_package = parts[-1] == '__init__'
        if is_package:
            parts.pop()
        for error in check_source(path.read_text(encoding='utf-8-sig'), '.'.join(parts),
                                  is_package=is_package):
            errors.append(f'{path}: {error}')
    return errors

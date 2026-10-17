import json
import os
import secrets
import time
from pathlib import Path


MAX_FILES = 500
PLAN_TTL_SECONDS = 900
MAX_SAVED_PLANS = 10

EXTENSION_CATEGORIES = {
    ".7z": "Archives", ".aac": "Audio", ".ai": "Images", ".aiff": "Audio",
    ".apk": "Installers", ".appx": "Installers", ".avi": "Video", ".bat": "Code",
    ".bmp": "Images", ".c": "Code", ".cab": "Installers", ".cmd": "Code",
    ".cpp": "Code", ".cs": "Code", ".css": "Code", ".csv": "Spreadsheets",
    ".doc": "Documents", ".docx": "Documents", ".flac": "Audio", ".gif": "Images",
    ".go": "Code", ".gz": "Archives", ".heic": "Images", ".html": "Code",
    ".ico": "Images", ".iso": "Installers", ".java": "Code", ".jpeg": "Images",
    ".jpg": "Images", ".js": "Code", ".json": "Code", ".m4a": "Audio",
    ".mkv": "Video", ".mov": "Video", ".mp3": "Audio", ".mp4": "Video",
    ".mpeg": "Video", ".msi": "Installers", ".ods": "Spreadsheets", ".odt": "Documents",
    ".pdf": "Documents", ".php": "Code", ".png": "Images", ".ppt": "Presentations",
    ".pptx": "Presentations", ".ps1": "Code", ".py": "Code", ".rar": "Archives",
    ".rb": "Code", ".rs": "Code", ".rtf": "Documents", ".scss": "Code",
    ".sh": "Code", ".sql": "Code", ".svg": "Images", ".tar": "Archives",
    ".tif": "Images", ".tiff": "Images", ".toml": "Code", ".ts": "Code",
    ".txt": "Documents", ".wav": "Audio", ".webm": "Video", ".webp": "Images",
    ".xls": "Spreadsheets", ".xlsx": "Spreadsheets", ".xml": "Code", ".yaml": "Code",
    ".yml": "Code", ".zip": "Archives",
}


def _result(**payload):
    return json.dumps(payload, ensure_ascii=True)


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _configured_roots(values):
    if not isinstance(values, list):
        return []
    roots = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            path = Path(value).expanduser()
            if path.is_dir() and not path.is_symlink():
                roots.append(path.resolve(strict=True))
        except (OSError, RuntimeError):
            continue
    return roots


def _validate_root(value, allowed_roots):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Choose a folder from the configured allowed folders.")
    if value.startswith(("\\\\?\\", "\\\\.\\")):
        raise ValueError("Windows device-namespace paths are not allowed.")
    candidate = Path(value).expanduser()
    if candidate.is_symlink():
        raise ValueError("A symbolic link cannot be used as the selected folder.")
    try:
        root = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("The selected folder does not exist or cannot be resolved.") from exc
    if not root.is_dir():
        raise ValueError("The selected path is not a folder.")
    if not any(_inside(root, allowed) for allowed in allowed_roots):
        raise ValueError("The selected folder is outside the configured allowed folders.")
    return root


def _category(path):
    return EXTENSION_CATEGORIES.get(path.suffix.lower(), "Other")


def _state_dict(state, key):
    value = state.get(key, default={})
    if not isinstance(value, dict):
        raise ValueError(f"Plugin state '{key}' is invalid; no files were changed.")
    return value


def preview_organize(args, allowed_roots, state):
    try:
        root = _validate_root(args.get("root"), allowed_roots)
        max_files = args.get("max_files", 200)
        if isinstance(max_files, bool) or not isinstance(max_files, int):
            raise ValueError("max_files must be an integer from 1 to 500.")
        max_files = min(max(1, max_files), MAX_FILES)

        entries = sorted(root.iterdir(), key=lambda path: path.name.casefold())
        files = []
        skipped = []
        for entry in entries:
            if entry.is_symlink() or not entry.is_file() or entry.name.startswith("."):
                continue
            if len(files) >= max_files:
                skipped.append({"name": entry.name, "reason": "max_files_limit"})
                continue
            category = _category(entry)
            target_dir = root / category
            if target_dir.is_symlink():
                skipped.append({"name": entry.name, "reason": "category_folder_is_symlink"})
                continue
            if target_dir.exists() and not target_dir.is_dir():
                skipped.append({"name": entry.name, "reason": "category_path_is_not_a_folder"})
                continue
            destination = target_dir / entry.name
            if os.path.lexists(destination):
                skipped.append({"name": entry.name, "reason": "destination_exists"})
                continue
            try:
                stat = entry.stat(follow_symlinks=False)
                files.append({
                    "source": str(entry),
                    "destination": str(destination),
                    "category": category,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                })
            except OSError:
                skipped.append({"name": entry.name, "reason": "file_unavailable"})

        plans = _state_dict(state, "plans")
        plan_id = secrets.token_urlsafe(18)
        plans[plan_id] = {"root": str(root), "created_at": time.time(), "files": files}
        plans = dict(sorted(plans.items(), key=lambda item: item[1].get("created_at", 0))[-MAX_SAVED_PLANS:])
        state.set("plans", plans)
        return _result(
            ok=True,
            plan_id=plan_id,
            root=str(root),
            planned=len(files),
            skipped=skipped,
            actions=[{"from": item["source"], "to": item["destination"]} for item in files],
            expires_in_seconds=PLAN_TTL_SECONDS,
            note="Preview only. No files were moved.",
        )
    except (OSError, ValueError, TypeError) as exc:
        return _result(ok=False, error=str(exc))


def _validate_plan(plan, allowed_roots):
    if not isinstance(plan, dict) or time.time() - plan.get("created_at", 0) > PLAN_TTL_SECONDS:
        raise ValueError("This preview is missing or expired. Create a new preview.")
    root = _validate_root(plan.get("root"), allowed_roots)
    files = plan.get("files")
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise ValueError("This preview is invalid. Create a new preview.")

    validated = []
    for item in files:
        source = Path(item.get("source", ""))
        destination = Path(item.get("destination", ""))
        category = _category(source)
        if source.parent != root or source.name != destination.name:
            raise ValueError("The preview contains an invalid source or destination.")
        if destination.parent != root / category:
            raise ValueError("The preview destination does not match the organization rules.")
        if source.is_symlink() or not source.is_file() or not _inside(source.resolve(strict=True), root):
            raise ValueError(f"Source is missing or unsafe: {source.name}")
        stat = source.stat(follow_symlinks=False)
        if stat.st_size != item.get("size") or stat.st_mtime_ns != item.get("mtime_ns"):
            raise ValueError(f"Source changed after preview: {source.name}. Create a new preview.")
        if os.path.lexists(destination):
            raise ValueError(f"Destination now exists: {destination.name}. Create a new preview.")
        if destination.parent.is_symlink():
            raise ValueError(f"Destination folder is a symbolic link: {category}")
        validated.append((source, destination))
    return root, validated


def _move_without_overwrite(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.parent.is_symlink() or os.path.lexists(destination):
        raise FileExistsError(f"Destination exists or is unsafe: {destination}")
    os.link(source, destination)
    try:
        source.unlink()
    except OSError:
        destination.unlink(missing_ok=True)
        raise


def _rollback_moves(moves):
    failures = []
    for source, destination in reversed(moves):
        try:
            if os.path.lexists(source) or not os.path.lexists(destination):
                raise FileExistsError("Rollback path is occupied or missing.")
            os.link(destination, source)
            destination.unlink()
        except OSError as exc:
            failures.append({"source": str(source), "destination": str(destination), "error": str(exc)})
    return failures


def apply_organize(args, allowed_roots, state):
    try:
        plans = _state_dict(state, "plans")
        plan_id = args.get("plan_id")
        root, files = _validate_plan(plans.get(plan_id), allowed_roots)
        if not files:
            raise ValueError("This preview has no files to move.")
        completed = []
        try:
            for source, destination in files:
                _move_without_overwrite(source, destination)
                completed.append((source, destination))
        except OSError as exc:
            rollback_failures = _rollback_moves(completed)
            return _result(
                ok=False,
                error=f"Move failed; completed moves were rolled back where possible: {exc}",
                rollback_failures=rollback_failures,
            )

        operation_id = secrets.token_urlsafe(18)
        operations = _state_dict(state, "operations")
        operations[operation_id] = {
            "root": str(root),
            "created_at": time.time(),
            "files": [{"source": str(src), "destination": str(dst)} for src, dst in completed],
        }
        operations = dict(sorted(operations.items(), key=lambda item: item[1].get("created_at", 0))[-MAX_SAVED_PLANS:])
        state.set("operations", operations)
        plans.pop(plan_id, None)
        state.set("plans", plans)
        return _result(ok=True, operation_id=operation_id, moved=len(completed), root=str(root))
    except (OSError, ValueError, TypeError) as exc:
        return _result(ok=False, error=str(exc))


def undo_organize(args, allowed_roots, state):
    try:
        operations = _state_dict(state, "operations")
        operation_id = args.get("operation_id")
        operation = operations.get(operation_id)
        if not isinstance(operation, dict):
            raise ValueError("Operation not found or already undone.")
        root = _validate_root(operation.get("root"), allowed_roots)
        files = operation.get("files")
        if not isinstance(files, list) or len(files) > MAX_FILES:
            raise ValueError("Operation record is invalid.")

        moves = []
        for item in files:
            source = Path(item.get("source", ""))
            destination = Path(item.get("destination", ""))
            category = _category(source)
            if source.parent != root or destination.parent != root / category:
                raise ValueError("Operation contains an unsafe path.")
            if destination.parent.is_symlink() or destination.is_symlink() or not destination.is_file():
                raise ValueError(f"Organized file is missing or unsafe: {destination.name}")
            if not _inside(destination.resolve(strict=True), root) or os.path.lexists(source):
                raise ValueError(f"Original location is occupied or destination is unsafe: {source.name}")
            moves.append((destination, source))

        completed = []
        try:
            for current, original in moves:
                _move_without_overwrite(current, original)
                completed.append((current, original))
        except OSError as exc:
            rollback_failures = _rollback_moves(completed)
            return _result(
                ok=False,
                error=f"Undo failed; completed restores were rolled back where possible: {exc}",
                rollback_failures=rollback_failures,
            )
        operations.pop(operation_id, None)
        state.set("operations", operations)
        return _result(ok=True, operation_id=operation_id, restored=len(completed), root=str(root))
    except (OSError, ValueError, TypeError) as exc:
        return _result(ok=False, error=str(exc))
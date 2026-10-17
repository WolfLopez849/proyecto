import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "file-organizer"
TOOLS_SPEC = importlib.util.spec_from_file_location("file_organizer_tools", PLUGIN_DIR / "tools.py")
tools = importlib.util.module_from_spec(TOOLS_SPEC)
TOOLS_SPEC.loader.exec_module(tools)


class MemoryState:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class FakeContext:
    def __init__(self, allowed_roots):
        self.allowed_roots = allowed_roots
        self.state = MemoryState()
        self.registered_tools = {}
        self.hooks = {}

    def get_config(self, key, default=None):
        return self.allowed_roots if key == "allowed_roots" else default

    def register_tool(self, name, toolset, schema, handler):
        self.registered_tools[name] = {"toolset": toolset, "schema": schema, "handler": handler}

    def register_hook(self, name, handler):
        self.hooks[name] = handler


def payload(response):
    return json.loads(response)


class FileOrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "Downloads"
        self.root.mkdir()
        self.allowed = [str(self.root)]
        self.state = MemoryState()

    def tearDown(self):
        self.temp.cleanup()

    def create_preview(self, file_name="photo.jpg"):
        (self.root / file_name).write_text("sample", encoding="utf-8")
        return payload(tools.preview_organize({"root": str(self.root)}, self.allowed, self.state))

    def test_preview_is_read_only_and_ignores_nested_files(self):
        (self.root / "photo.jpg").write_text("sample", encoding="utf-8")
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "secret.pdf").write_text("sample", encoding="utf-8")

        result = payload(tools.preview_organize({"root": str(self.root)}, self.allowed, self.state))

        self.assertTrue(result["ok"])
        self.assertEqual(result["planned"], 1)
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertFalse((self.root / "Images" / "photo.jpg").exists())
        self.assertNotIn("secret.pdf", str(result["actions"]))

    def test_preview_rejects_folder_outside_allowlist(self):
        outside = Path(self.temp.name) / "Elsewhere"
        outside.mkdir()
        result = payload(tools.preview_organize({"root": str(outside)}, self.allowed, self.state))
        self.assertFalse(result["ok"])
        self.assertIn("outside", result["error"])

    def test_apply_moves_files_and_undo_restores_them(self):
        preview = self.create_preview()
        applied = payload(tools.apply_organize({"plan_id": preview["plan_id"]}, self.allowed, self.state))

        self.assertTrue(applied["ok"])
        organized = self.root / "Images" / "photo.jpg"
        self.assertTrue(organized.exists())
        self.assertFalse((self.root / "photo.jpg").exists())

        undone = payload(tools.undo_organize({"operation_id": applied["operation_id"]}, self.allowed, self.state))
        self.assertTrue(undone["ok"])
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertFalse(organized.exists())

    def test_apply_refuses_file_changed_after_preview(self):
        preview = self.create_preview()
        file_path = self.root / "photo.jpg"
        file_path.write_text("changed content", encoding="utf-8")

        result = payload(tools.apply_organize({"plan_id": preview["plan_id"]}, self.allowed, self.state))

        self.assertFalse(result["ok"])
        self.assertIn("changed after preview", result["error"])
        self.assertTrue(file_path.exists())

    def test_apply_refuses_destination_collision(self):
        preview = self.create_preview()
        destination = self.root / "Images" / "photo.jpg"
        destination.parent.mkdir()
        destination.write_text("keep", encoding="utf-8")

        result = payload(tools.apply_organize({"plan_id": preview["plan_id"]}, self.allowed, self.state))

        self.assertFalse(result["ok"])
        self.assertIn("Destination now exists", result["error"])
        self.assertEqual(destination.read_text(encoding="utf-8"), "keep")

    def test_expired_plan_is_rejected(self):
        preview = self.create_preview()
        self.state.values["plans"][preview["plan_id"]]["created_at"] -= tools.PLAN_TTL_SECONDS + 1

        result = payload(tools.apply_organize({"plan_id": preview["plan_id"]}, self.allowed, self.state))

        self.assertFalse(result["ok"])
        self.assertIn("expired", result["error"])

    def test_plugin_registers_tools_and_human_approval_hook(self):
        package_name = "file_organizer_plugin_test"
        package_spec = importlib.util.spec_from_file_location(
            package_name,
            PLUGIN_DIR / "__init__.py",
            submodule_search_locations=[str(PLUGIN_DIR)],
        )
        plugin = importlib.util.module_from_spec(package_spec)
        sys.modules[package_name] = plugin
        try:
            package_spec.loader.exec_module(plugin)
            context = FakeContext(self.allowed)
            plugin.register(context)
        finally:
            sys.modules.pop(package_name, None)
            sys.modules.pop(f"{package_name}.schemas", None)
            sys.modules.pop(f"{package_name}.tools", None)

        self.assertEqual(set(context.registered_tools), {
            "file_organizer_preview", "file_organizer_apply", "file_organizer_undo"
        })
        approval = context.hooks["pre_tool_call"]
        self.assertEqual(approval("file_organizer_apply", {})["action"], "approve")
        self.assertEqual(approval("file_organizer_undo", {})["action"], "approve")
        self.assertIsNone(approval("file_organizer_preview", {}))


if __name__ == "__main__":
    unittest.main()
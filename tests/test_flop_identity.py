import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

import flop_identity as helper


class PureFunctionTests(unittest.TestCase):
    def test_sweep_replaces_invisible_characters(self):
        self.assertEqual(helper.sweep("hello\u202eworld", 100), "hello world")

    def test_name_validation_fails_closed(self):
        for invalid in ("Upper", "has space", "../room", "", "a" * 49):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                helper.validate_name(invalid, "room")

    def test_nonce_validation_fails_closed(self):
        for invalid in ("", "-1", "1.0", "1e3", "1" * 20):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                helper.validate_nonce(invalid)

    def test_no_network_capable_imports(self):
        source = Path(helper.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        banned = {"http", "httpx", "requests", "socket", "urllib3", "webbrowser"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported & banned, set())


@unittest.skipUnless(os.name == "nt", "Windows DPAPI test")
class WindowsIntegrationTests(unittest.TestCase):
    def test_selftest(self):
        result = helper.selftest()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["dpapi_roundtrip"], "ok")
        self.assertEqual(result["network_requests"], "0")

    def test_init_does_not_overwrite_and_prepare_does_not_send(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp) / "identity"
            created = helper.create_identity(store)
            self.assertEqual(created["secret_exposed"], "no")
            with self.assertRaises(FileExistsError):
                helper.create_identity(store)

            prepared = helper.prepare_message(store, "test-room", "1", "safe proof")
            self.assertEqual(prepared["sent"], "no")
            self.assertEqual(prepared["room"], "test-room")
            self.assertTrue(prepared["write_url"].startswith("https://technocore.chat/"))
            self.assertEqual(len(prepared["signature"]), 86)

            note = helper.prepare_did_note(store)
            self.assertEqual(note["sent"], "no")
            self.assertEqual(note["did"], created["did"])

            public = json.loads((store / helper.PUBLIC_FILE).read_text(encoding="utf-8"))
            self.assertNotIn("seed", public)
            self.assertNotIn("private", public)


if __name__ == "__main__":
    unittest.main()


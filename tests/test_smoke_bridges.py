import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nych_smoke.b5 import lookup_gst
from nych_smoke.symbolizer_stub import LiteralSymbolizerStub


class GSTBridgeTests(unittest.TestCase):
    def test_b5_uses_explicit_b4_keys_and_read_only_connection(self):
        class Connection:
            def close(self):
                self.closed = True

        class Context:
            def as_dict(self):
                return {"gst_version": "NYCH-GST-CONTEXT-V1", "status": "HIT"}

        class Module:
            def __init__(self):
                self.args = None

            def lookup_loop(self, connection, **kwargs):
                self.args = (connection, kwargs)
                return Context()

        module = Module()
        connection = Connection()
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "tote_loops.sqlite3"
            db_path.touch()
            with patch("nych_smoke.b5.gst_context_module", return_value=module), patch(
                "nych_smoke.b5.sqlite3.connect", return_value=connection
            ) as connect:
                output = lookup_gst(db_path, domain_id="domain-1", action_key="repair widget")
        self.assertEqual(output["status"], "HIT")
        self.assertEqual(module.args[0], connection)
        self.assertEqual(module.args[1]["domain_id"], "domain-1")
        self.assertEqual(module.args[1]["action_key"], "repair widget")
        self.assertTrue(connect.call_args.kwargs["uri"])
        self.assertTrue(connect.call_args.args[0].endswith("?mode=ro"))
        self.assertTrue(connection.closed)


class SymbolizerBoundaryTests(unittest.TestCase):
    def test_stub_keeps_gst_and_prompt_as_separate_in_memory_channels(self):
        gst = {"status": "CACHE_MISS", "tote": None}
        # Opaque non-language sentinel: the test must not contain a raw prompt.
        prompt = chr(0xE000) * 4
        stub = LiteralSymbolizerStub()
        result = stub(gst, prompt, [(0, len(prompt.encode("utf-8")))])
        self.assertIs(stub.calls[0][0], gst)
        self.assertEqual(stub.calls[0][1], prompt)
        self.assertEqual(result[0]["selection"], "LITERAL")
        self.assertNotIn(prompt, json.dumps(result))


if __name__ == "__main__":
    unittest.main()

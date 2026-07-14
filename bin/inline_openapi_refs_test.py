import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from inline_openapi_refs import (
    _apply_additive_patches,
)


class AdditivePatchTests(unittest.TestCase):
    def test_document_fields_merge_into_generated_document(self) -> None:
        doc = {
            "info": {"title": "Upstream API", "version": "1.0.0"},
            "paths": {"/responses": {"post": {"summary": "Create"}}},
        }
        patches = {
            "version": 1,
            "add": {
                "document_fields": [
                    {
                        "path": "/info",
                        "merge": {
                            "title": "Open Responses",
                            "version": "2026-04-24",
                        },
                    },
                    {
                        "path": "/paths/~1responses/post",
                        "merge": {"x-openresponses-added-in": "2026-04-24"},
                    },
                ]
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            patches_path = Path(directory) / "patches.json"
            patches_path.write_text(json.dumps(patches), encoding="utf-8")
            result = _apply_additive_patches(doc, patches_path=patches_path)

        self.assertEqual(result["info"]["title"], "Open Responses")
        self.assertEqual(result["info"]["version"], "2026-04-24")
        self.assertEqual(
            result["paths"]["/responses"]["post"]["x-openresponses-added-in"],
            "2026-04-24",
        )
if __name__ == "__main__":
    unittest.main()

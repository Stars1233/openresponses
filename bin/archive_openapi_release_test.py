import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from archive_openapi_release import _release_version, archive_release


class ArchiveOpenApiReleaseTests(unittest.TestCase):
    def test_release_version_requires_a_calendar_date(self) -> None:
        self.assertEqual(
            _release_version({"info": {"version": "2026-04-24"}}),
            "2026-04-24",
        )
        with self.assertRaisesRegex(RuntimeError, "YYYY-MM-DD"):
            _release_version({"info": {"version": "2026-02-30"}})

    def test_creates_an_exact_copy_of_the_canonical_document(self) -> None:
        content = '{\n  "info": {"version": "2026-04-24"},\n  "paths": {}\n}\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "current.json"
            input_path.write_text(content, encoding="utf-8")

            output_path, created = archive_release(input_path, root / "releases")

            self.assertTrue(created)
            self.assertEqual(output_path.read_text(encoding="utf-8"), content)

    def test_keeps_a_semantically_identical_release_byte_for_byte(self) -> None:
        canonical = {"info": {"version": "2026-04-24"}, "paths": {}}
        existing_content = '{"paths":{},"info":{"version":"2026-04-24"}}\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "current.json"
            input_path.write_text(json.dumps(canonical), encoding="utf-8")
            output_path = root / "releases" / "2026-04-24" / "openapi.json"
            output_path.parent.mkdir(parents=True)
            output_path.write_text(existing_content, encoding="utf-8")

            returned_path, created = archive_release(input_path, root / "releases")

            self.assertFalse(created)
            self.assertEqual(returned_path, output_path)
            self.assertEqual(output_path.read_text(encoding="utf-8"), existing_content)

    def test_rejects_a_conflicting_release_without_changing_either_file(self) -> None:
        canonical_content = '{"info":{"version":"2026-04-24"},"paths":{}}'
        release_content = '{"info":{"version":"2026-04-24"},"paths":{"/old":{}}}'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "current.json"
            input_path.write_text(canonical_content, encoding="utf-8")
            output_path = root / "releases" / "2026-04-24" / "openapi.json"
            output_path.parent.mkdir(parents=True)
            output_path.write_text(release_content, encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "Refusing to overwrite"):
                archive_release(input_path, root / "releases")

            self.assertEqual(input_path.read_text(encoding="utf-8"), canonical_content)
            self.assertEqual(output_path.read_text(encoding="utf-8"), release_content)

    def test_rejects_a_malformed_existing_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "current.json"
            input_path.write_text(
                '{"info":{"version":"2026-04-24"}}',
                encoding="utf-8",
            )
            output_path = root / "releases" / "2026-04-24" / "openapi.json"
            output_path.parent.mkdir(parents=True)
            output_path.write_text("not json", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "Cannot read existing release"):
                archive_release(input_path, root / "releases")


if __name__ == "__main__":
    unittest.main()

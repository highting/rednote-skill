import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_content_template import _bundled_chinese_css
from scripts.download_content_fonts import download_content_fonts


class ContentFontTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.font = b"wOF2" + b"test-font-bytes"
        self.package = self.root / "package"
        (self.package / "files").mkdir(parents=True)
        self.source = self.package / "files/test.woff2"
        self.source.write_bytes(self.font)
        self.manifest = self.root / "font-manifest.json"
        self.manifest.write_text(json.dumps({
            "family": "Noto Sans SC", "weight": 400, "fontsource_version": "5.3.0",
            "base_url": "https://example.invalid/",
            "faces": [{"source": "test.woff2", "unicode_range": "U+4E00-9FFF",
                       "bytes": len(self.font), "sha256": hashlib.sha256(self.font).hexdigest()}],
        }), encoding="utf-8")
        self.output = self.root / "font-bundle.json"

    def build_cache(self):
        return download_content_fonts(source_dir=self.package, manifest_path=self.manifest, output=self.output)

    def test_local_package_creates_cache_and_complete_cache_needs_no_network(self):
        result = self.build_cache()
        self.assertFalse(result["cached"])
        bundle = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(base64.b64decode(bundle["faces"][0]["data"]), self.font)
        with patch("scripts.download_content_fonts.urlopen", side_effect=AssertionError("Unexpected network request")):
            result = download_content_fonts(manifest_path=self.manifest, output=self.output)
        self.assertTrue(result["cached"])
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_bad_download_does_not_replace_existing_cache(self):
        previous = b"previous incomplete cache"
        self.output.write_bytes(previous)
        self.source.write_bytes(b"wOF2" + b"corrupt-bytes!!")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.build_cache()
        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_changed_cached_font_is_repaired_from_verified_package(self):
        self.build_cache()
        bundle = json.loads(self.output.read_text(encoding="utf-8"))
        bundle["faces"][0]["data"] = base64.b64encode(b"wOF2-corrupt").decode("ascii")
        self.output.write_text(json.dumps(bundle), encoding="utf-8")
        self.assertFalse(self.build_cache()["cached"])
        bundle = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(base64.b64decode(bundle["faces"][0]["data"]), self.font)

    def test_missing_cache_explains_download_or_custom_font(self):
        with self.assertRaisesRegex(ValueError, r"download_content_fonts\.py.*--font"):
            _bundled_chinese_css(self.output, "中文")


if __name__ == "__main__":
    unittest.main()

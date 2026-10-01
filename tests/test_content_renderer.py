import hashlib
import importlib.util
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.render_content import check_self_contained_html, render_content

BROWSER = os.environ.get("CONTENT_RENDER_BROWSER_EXECUTABLE")
if not BROWSER:
    candidate = Path(__file__).resolve().parents[2] / "prompt-lab/runtime/chromium"
    if candidate.is_file():
        BROWSER = str(candidate)
HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None


def html(body, css="", script=""):
    return '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}'+css+'</style></head><body>'+body+'<script>'+script+'</script></body></html>'


def png_size(path):
    raw = Path(path).read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", raw[16:24])


class ContentResourceTests(unittest.TestCase):
    def test_self_contained_assets_and_citation_links(self):
        source = html('<a href="https://example.org/paper">citation</a><img src="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'1\' height=\'1\'/%3E">')
        self.assertEqual(check_self_contained_html(source), [])

    def test_local_and_remote_resources_are_rejected(self):
        for source in [
            html('<img src="relative.png">'),
            html('<script src="https://example.org/app.js"></script>'),
            html("", "@font-face{font-family:test;src:url(font.woff2)}"),
            html('<link rel="stylesheet" href="style.css">'),
            html("", '@import "https://example.org/style.css";'),
        ]:
            with self.subTest(source=source):
                self.assertTrue(check_self_contained_html(source))


@unittest.skipUnless(HAS_PLAYWRIGHT and BROWSER, "Set CONTENT_RENDER_BROWSER_EXECUTABLE and install the existing Playwright dependency")
class ContentRendererBrowserTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    async def render(self, source, scene="learning", **kwargs):
        entry = self.root / "source.html"
        entry.write_text(source, encoding="utf-8")
        self.output = self.root / ("out-" + scene)
        qa = await render_content(entry, self.output, scene=scene, browser_executable=BROWSER, **kwargs)
        self.assertEqual(json.loads((self.output / "qa.json").read_text()), qa)
        return qa, entry

    def assert_passed(self, qa, entry):
        self.assertTrue(qa["passed"], qa["errors"])
        self.assertEqual(qa["schema_version"], 1)
        self.assertEqual(qa["html_sha256"], hashlib.sha256((self.output / "index.html").read_bytes()).hexdigest())
        self.assertEqual(entry.read_bytes(), (self.output / "index.html").read_bytes())
        self.assertFalse(qa["semantic_validation"]["performed"])
        for image in qa["images"]:
            self.assertEqual(png_size(self.output / image["file"]), (image["width"], image["height"]))

    async def test_learning_defaults_to_portable_html_and_desktop_preview(self):
        source = html('<nav data-export-ui>Directory</nav><article><h1>Learning</h1>'+("<p>Complete paragraph.</p>"*80)+"</article>", "article{width:760px;margin:auto;font-size:18px;line-height:2}")
        qa, entry = await self.render(source)
        self.assert_passed(qa, entry)
        self.assertEqual(qa["scene"], "learning")
        self.assertEqual(qa["checks"]["export_ui"], {"marked": 1, "visible": 1})
        self.assertEqual([i["file"] for i in qa["images"]], ["preview.png"])
        self.assertEqual(png_size(self.output / "preview.png"), (1440, 1000))
        self.assertFalse((self.output / "page-01.png").exists())

    async def test_blog_full_document_png_requires_explicit_opt_in(self):
        source = html('<article>'+("<p>Complete paragraph.</p>"*80)+"</article>", "article{width:760px;margin:auto;font-size:18px;line-height:2}")
        qa, entry = await self.render(source, "blog", export_images=True)
        self.assert_passed(qa, entry)
        self.assertEqual([i["kind"] for i in qa["images"]], ["preview", "full-document"])
        self.assertGreater(png_size(self.output / "page-01.png")[1], 1000)

    async def test_report_exports_explicit_pages_without_preview_scaling(self):
        source = html('<div style="transform:scale(.5);transform-origin:top left"><section data-export-page><h1>First</h1><button data-export-ui>UI</button></section><section data-export-page><h1>Second</h1></section></div>', "[data-export-page]{width:1280px;height:720px;box-sizing:border-box;padding:30px;background:#faf9f5}h1{margin:0}")
        qa, entry = await self.render(source, "report", dpr=1)
        self.assert_passed(qa, entry)
        self.assertEqual([i["file"] for i in qa["images"]], ["page-01.png", "page-02.png"])
        self.assertEqual(png_size(self.output / "page-02.png"), (1280, 720))
        self.assertEqual(qa["checks"]["export_ui"], {"marked": 1, "visible": 0})

    async def test_rednote_exports_only_marked_3_by_4_pages(self):
        source = html('<section data-export-page><h1>One</h1></section><section data-export-page><h1>Two</h1></section>', "[data-export-page]{width:1080px;height:1440px;box-sizing:border-box;padding:40px}h1{margin:0}")
        qa, entry = await self.render(source, "rednote")
        self.assert_passed(qa, entry)
        self.assertEqual(len(qa["images"]), 2)
        self.assertEqual(png_size(self.output / "page-01.png"), (1080, 1440))

    async def test_diagram_exports_figure_with_its_own_dimensions(self):
        source = html('<figure data-export-figure><svg viewBox="0 0 320 200"><rect x="20" y="20" width="200" height="120"/></svg></figure>', "figure{margin:0;width:320px;height:200px}svg{display:block;width:100%;height:100%}")
        qa, entry = await self.render(source, "diagram", dpr=2)
        self.assert_passed(qa, entry)
        self.assertEqual(png_size(self.output / "page-01.png"), (640, 400))

    async def test_long_document_is_not_automatically_sliced_into_rednote(self):
        qa, _ = await self.render(html('<article>'+("<p>Paragraph</p>"*80)+"</article>"), "rednote")
        self.assertFalse(qa["passed"])
        self.assertIn("does not paginate", qa["errors"][0])
        self.assertFalse((self.output / "index.html").exists())

    async def test_local_resource_rejected_without_copying_broken_html(self):
        qa, _ = await self.render(html('<img src="relative.png">'))
        self.assertFalse(qa["passed"])
        self.assertIsNone(qa["html_sha256"])
        self.assertEqual(qa["images"], [])
        self.assertFalse((self.output / "index.html").exists())

    async def test_runtime_network_request_and_console_errors_are_rejected(self):
        for script in [
            'fetch("https://example.org/asset.json").catch(()=>{});',
            'console.error("intentional error");',
            'throw new Error("intentional pageerror");',
        ]:
            with self.subTest(script=script):
                qa, _ = await self.render(html("<p>Text</p>", script=script))
                self.assertFalse(qa["passed"])
                self.assertFalse((self.output / "index.html").exists())

    async def test_missing_embedded_image_is_rejected(self):
        qa, _ = await self.render(html('<img src="data:image/png;base64,AAAA">'))
        self.assertFalse(qa["passed"])
        self.assertTrue(any("image" in message.lower() for message in qa["errors"]))

    async def test_page_overflow_and_clipped_text_are_rejected(self):
        qa, _ = await self.render(html('<section data-export-page><div style="height:900px">Too tall</div></section>', "[data-export-page]{width:1280px;height:720px;overflow:hidden}"), "report")
        self.assertFalse(qa["passed"])
        self.assertTrue(any("overflow" in error or "frame" in error for error in qa["errors"]))
        qa, _ = await self.render(html('<div style="width:200px;height:20px;overflow:hidden"><p style="height:80px">Clipped text</p></div>'))
        self.assertFalse(qa["passed"])
        self.assertTrue(any("Clipped" in error for error in qa["errors"]))

    async def test_hidden_pages_require_explicit_activation_hook(self):
        body = '<section data-export-page>First</section><section data-export-page style="display:none">Second</section>'
        css = "[data-export-page]{width:1280px;height:720px}"
        qa, _ = await self.render(html(body, css), "report")
        self.assertFalse(qa["passed"])
        self.assertTrue(any("hidden" in error for error in qa["errors"]))
        script = 'window.activate=({index})=>document.querySelectorAll("[data-export-page]").forEach((e,i)=>e.style.display=i===index?"block":"none");'
        qa, entry = await self.render(html(body, css, script), "report", activate_hook="activate")
        self.assert_passed(qa, entry)
        self.assertEqual(len(qa["images"]), 2)

    async def test_continuous_document_allows_accessible_scrollers_but_full_png_rejects_clipping(self):
        content = '<nav data-allow-scroll style="width:220px;height:80px;overflow:auto">'+('<p><a href="#text">Directory item</a></p>'*12)+'</nav><p id="text">Article</p>'
        qa, entry = await self.render(html(content))
        self.assert_passed(qa, entry)
        code = '<pre data-allow-scroll style="width:200px;overflow:auto">'+('longword '*80)+'</pre>'
        qa, entry = await self.render(html(code))
        self.assert_passed(qa, entry)
        # A full PNG cannot retain the scroller's off-screen content.
        qa, _ = await self.render(html(code), export_images=True)
        self.assertFalse(qa["passed"])
        self.assertTrue(any("Clipped" in error for error in qa["errors"]))

    async def test_default_preview_audits_original_wide_directory_ui(self):
        source = html('<nav data-export-ui style="width:3000px">Directory</nav><article>Text</article>')
        qa, _ = await self.render(source)
        self.assertFalse(qa["passed"])
        self.assertEqual(qa["checks"]["export_ui"], {"marked": 1, "visible": 1})
        self.assertTrue(any("horizontal overflow" in error for error in qa["errors"]))

    async def test_shrinking_page_count_cleans_only_recorded_generated_files_after_success(self):
        css = "[data-export-page]{width:1280px;height:720px}"
        pages = lambda count: "".join('<section data-export-page>Page '+str(i)+'</section>' for i in range(count))
        qa, entry = await self.render(html(pages(8), css), "report")
        self.assert_passed(qa, entry)
        previous_index = (self.output / "index.html").read_bytes()
        previous_last = (self.output / "page-08.png").read_bytes()
        (self.output / "artwork.png").write_bytes(b"user asset")
        (self.output / "title.txt").write_text("keep me")
        outside = self.root / "outside.png"
        outside.write_bytes(b"outside asset")
        # An untrusted QA filename must never escape the delivery directory.
        record = json.loads((self.output / "qa.json").read_text())
        record["images"].append({"file": "../outside.png"})
        (self.output / "qa.json").write_text(json.dumps(record))
        bad = html('<section data-export-page><div style="height:900px">overflow</div></section>', css)
        failed, _ = await self.render(bad, "report")
        self.assertFalse(failed["passed"])
        self.assertEqual((self.output / "index.html").read_bytes(), previous_index)
        self.assertEqual((self.output / "page-08.png").read_bytes(), previous_last)
        qa, entry = await self.render(html(pages(6), css), "report")
        self.assert_passed(qa, entry)
        self.assertFalse((self.output / "page-07.png").exists())
        self.assertFalse((self.output / "page-08.png").exists())
        self.assertEqual((self.output / "artwork.png").read_bytes(), b"user asset")
        self.assertEqual((self.output / "title.txt").read_text(), "keep me")
        self.assertEqual(outside.read_bytes(), b"outside asset")

    async def test_math_internal_svg_is_not_misreported_as_visible_overflow(self):
        source = html('<p>Formula <span class="katex" style="display:inline-block;width:120px;height:40px;overflow:hidden"><svg width="4000" height="40"><path d="M0 20 L4000 20"/></svg></span></p>')
        qa, entry = await self.render(source)
        self.assert_passed(qa, entry)


if __name__ == "__main__":
    unittest.main()

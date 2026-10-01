from pathlib import Path
import asyncio
import tempfile
import unittest

from scripts.build_content_template import build_content_template


class ContentTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_four_scenes_are_offline_starting_points(self):
        for scene in ("learning", "blog", "report", "rednote"):
            with self.subTest(scene=scene):
                result = build_content_template(scene, self.root / scene)
                html = Path(result["output"]).read_text(encoding="utf-8")
                self.assertTrue(result["template_example"])
                self.assertTrue(result["embedded_chinese_font"])
                self.assertEqual(result["chinese_font_source"], "bundled-noto-sans-sc")
                self.assertGreater(result["chinese_font_faces"], 0)
                self.assertIn('data-content-scene="' + scene + '"', html)
                self.assertIn("模板示例", html)
                self.assertIn("data:font/woff2;base64,", html)
                self.assertNotRegex(html, r'<(?:script|link)\b[^>]*(?:src|href)=["\'](?:https?:|fonts/)')
                self.assertNotRegex(html, r"\{\{(?:TITLE|STYLE|MATH_SCRIPT|SHARED_SCRIPT|LICENSE)\}\}")
                self.assertIn("activateContentExport", html)
                self.assertEqual(result["explicit_pages"], 2 if scene in ("report", "rednote") else 0)

    def test_title_escapes_markup_and_body_keeps_authored_text(self):
        body = self.root / "article.html"
        body.write_text('<section><h2 id="real">作者正文</h2><p>必须保留的内容。</p></section>', encoding="utf-8")
        result = build_content_template("blog", self.root / "article-out.html", title="A < B & C", body_file=body)
        html = Path(result["output"]).read_text(encoding="utf-8")
        self.assertIn("A &lt; B &amp; C", html)
        self.assertIn("必须保留的内容。", html)
        self.assertNotIn('id="blog-question"', html)
        self.assertFalse(result["template_example"])

    def test_body_local_images_inline_and_citation_links_remain(self):
        image = self.root / "plot.svg"
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        body = self.root / "body.html"
        body.write_text('<p><img src="plot.svg" alt="作者配图"><a href="https://example.org/paper">来源</a></p>', encoding="utf-8")
        result = build_content_template("learning", self.root / "images.html", body_file=body)
        html = Path(result["output"]).read_text(encoding="utf-8")
        self.assertIn('src="data:image/svg+xml;base64,', html)
        self.assertIn('href="https://example.org/paper"', html)
        body.write_text('<img src="https://example.org/image.png">', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Offline resources"):
            build_content_template("learning", self.root / "remote.html", body_file=body)

    def test_fixed_scene_requires_explicit_pages(self):
        body = self.root / "body.html"
        body.write_text('<h2>没有显式页面</h2>', encoding="utf-8")
        for scene in ("report", "rednote"):
            with self.assertRaisesRegex(ValueError, "data-export-page"):
                build_content_template(scene, self.root / scene, body_file=body)
        body.write_text('<section class="report-page" data-export-page><h2>作者页面</h2></section>', encoding="utf-8")
        self.assertEqual(build_content_template("report", self.root / "report", body_file=body)["explicit_pages"], 1)

    def test_css_resources_embed_without_rewriting_code_samples(self):
        (self.root / "plot.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        body = self.root / "body.html"
        body.write_text('<pre><code>url("not-a-resource.png")</code></pre><img src=plot.svg><div style="background:url(\'plot.svg\')"></div>', encoding="utf-8")
        html = Path(build_content_template("blog", self.root / "css.html", body_file=body)["output"]).read_text(encoding="utf-8")
        self.assertIn('url("not-a-resource.png")', html)
        self.assertIn('src="data:image/svg+xml;base64,', html)
        self.assertIn('background:url(&quot;data:image/svg+xml;base64,', html)

    def test_report_navigation_preserves_directory_state_and_prevents_page_scroll(self):
        from playwright.async_api import async_playwright

        document = Path(build_content_template("report", self.root / "report.html")["output"])

        async def check():
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
                try:
                    page = await browser.new_page(viewport={"width": 1440, "height": 1000})
                    await page.goto(document.as_uri())
                    await page.evaluate("window.contentExport.ready")
                    self.assertTrue(await page.locator("[data-report-toc]").is_hidden())
                    await page.locator("[data-report-toc-toggle]").click()
                    await page.locator('[data-slide-target="1"]').click()
                    self.assertEqual(await page.locator("[data-page-counter]").inner_text(), "2 / 2")
                    for key, expected in [("PageUp", "1 / 2"), ("PageDown", "2 / 2"), ("ArrowRight", "2 / 2"), ("ArrowLeft", "1 / 2"), ("PageUp", "1 / 2")]:
                        await page.keyboard.press(key)
                        self.assertEqual(await page.locator("[data-page-counter]").inner_text(), expected)
                        self.assertEqual(await page.evaluate("scrollY"), 0)
                        self.assertTrue(await page.locator("[data-report-toc]").is_visible())
                    await page.evaluate("""() => {const input=document.createElement('input'); input.id='local-input'; document.querySelector('.report-page:not([hidden])').append(input); input.focus();}""")
                    await page.keyboard.press("PageDown")
                    self.assertEqual(await page.locator("[data-page-counter]").inner_text(), "1 / 2")
                    await page.locator("#local-input").evaluate("el=>el.remove()")
                    await page.evaluate("window.activateContentExport({index:1,scene:'report'})")
                    box = await page.locator("[data-export-page]").nth(1).bounding_box()
                    self.assertEqual((box["width"], box["height"]), (1280, 720))
                    self.assertEqual(await page.evaluate("window.contentExport.state.mathErrors"), [])
                finally:
                    await browser.close()

        asyncio.run(check())

    def test_font_is_optional_but_explicit_embedding_adds_mixed_text_fallback(self):
        font = self.root / "test.woff2"
        font.write_bytes(b"font test fixture")
        result = build_content_template("learning", self.root / "font.html", font=font)
        html = Path(result["output"]).read_text(encoding="utf-8")
        self.assertTrue(result["embedded_chinese_font"])
        self.assertIn('font-family:"ContentEmbeddedChinese"', html)
        self.assertIn('.katex .cjk_fallback{font-family:var(--content-font-zh)}', html)
        self.assertIn('"DejaVu Sans Mono",var(--content-font-zh),monospace', html)

    def test_source_frames_reserve_footer_space_and_declare_sizes(self):
        assets = Path(__file__).resolve().parent.parent / "assets/content"
        css = (assets / "shared.css").read_text(encoding="utf-8")
        self.assertRegex(css, r'\.report-page\{width:1280px;height:720px;')
        self.assertRegex(css, r'\.rednote-page\{width:1080px;height:1440px;')
        self.assertIn('grid-template-rows:minmax(0,1fr)56px', css)
        self.assertIn('grid-template-rows:minmax(0,1fr)90px', css)


if __name__ == "__main__":
    unittest.main()

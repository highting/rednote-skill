#!/usr/bin/env python3
"""Build an offline scene starting point; never invent technical article text."""

import argparse
import base64
from html import escape, unescape
from html.parser import HTMLParser
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENES = ("learning", "blog", "report", "rednote")
DEFAULT_TITLES = {
    "learning": "个人学习文档：源码模板示例",
    "blog": "技术博客：源码模板示例",
    "report": "技术汇报：源码模板示例",
    "rednote": "小红书图文：源码模板示例",
}


def _bundled_chinese_css(bundle_path: Path, text: str):
    """Select cached Unicode faces; the package is licensed alongside the bundle."""
    if not bundle_path.is_file():
        raise ValueError(
            "Chinese font cache is missing. Run "
            "python -X utf8 scripts/download_content_fonts.py first, "
            "or pass --font /path/to/licensed-font.woff2. "
            f"Expected cache: {bundle_path}"
        )
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    points = set(map(ord, text))
    selected = []
    for face in bundle["faces"]:
        ranges = []
        for value in face["unicode_range"].split(","):
            bounds = value.strip().removeprefix("U+").removeprefix("u+").split("-")
            start = int(bounds[0].replace("?", "0"), 16)
            end = int(bounds[-1].replace("?", "F"), 16)
            ranges.append((start, end))
        if any(start <= point <= end for point in points for start, end in ranges):
            selected.append('@font-face{font-family:"Noto Sans SC";font-style:normal;font-weight:400;src:url("data:font/woff2;base64,' + face["data"] + '") format("woff2");unicode-range:' + face["unicode_range"] + ';}')
    return "\n".join(selected), len(selected)


def _data_url(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"Local resource does not exist: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _embed_url(value: str, base: Path) -> str:
    value = unescape(value).strip()
    if not value or value.startswith(("data:", "#")):
        return value
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"Offline resources must be local or data URLs: {value}")
    path = (base / unquote(parsed.path)).resolve()
    return _data_url(path) + ("#" + parsed.fragment if parsed.fragment else "")


def _embed_css(css: str, base: Path) -> str:
    if re.search(r"@import\b", css, re.I):
        raise ValueError("CSS @import is not supported in a self-contained document")
    return re.sub(
        r"url\(\s*(['\"]?)(.*?)\1\s*\)",
        lambda match: 'url("' + _embed_url(match[2], base) + '")', css,
        flags=re.I,
    )


def _embed_body_resources(body: str, base: Path) -> str:
    """Inline resource attributes; ordinary source/citation <a> links stay links."""
    if re.search(r"\bsrcset\s*=", body, re.I):
        raise ValueError("Use one local/data src per image; srcset is not supported")
    if re.search(r"<link\b", body, re.I):
        raise ValueError("Put body styles inline; external <link> resources are not supported")

    def replace_tag(match):
        tag = match[0]
        # src/poster applies to images, media, and explicitly trusted script fragments.
        attrs = r"(\b(?:src|poster)\s*=\s*)(?:(['\"])(.*?)\2|([^\s>]+))"
        tag = re.sub(attrs, lambda m: m[1] + (m[2] or '"') + _embed_url(m[3] if m[2] else m[4], base) + (m[2] or '"'), tag, flags=re.I)
        if re.match(r"<\s*(?:image|use)\b", tag, re.I):
            tag = re.sub(r"(\b(?:href|xlink:href)\s*=\s*)(['\"])(.*?)\2", lambda m: m[1] + m[2] + _embed_url(m[3], base) + m[2], tag, flags=re.I)
        if re.match(r"<\s*object\b", tag, re.I):
            tag = re.sub(r"(\bdata\s*=\s*)(['\"])(.*?)\2", lambda m: m[1] + m[2] + _embed_url(m[3], base) + m[2], tag, flags=re.I)
        tag = re.sub(r"(\bstyle\s*=\s*)(['\"])(.*?)\2", lambda m: m[1] + m[2] + escape(_embed_css(unescape(m[3]), base), quote=True) + m[2], tag, flags=re.I)
        return tag

    body = re.sub(r"<[^>]+>", replace_tag, body)
    # CSS-like text in code/prose is authored content, not a resource reference.
    return re.sub(r"(<style\b[^>]*>)(.*?)(</style\s*>)", lambda m: m[1] + _embed_css(m[2], base) + m[3], body, flags=re.I | re.S)


class _PageCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if any(key == "data-export-page" for key, _ in attrs):
            self.count += 1


def build_content_template(scene: str, output, *, title=None, body_file=None, font=None, project_root=None):
    """Return build metadata; body_file must contain already-written trusted HTML."""
    if scene not in SCENES:
        raise ValueError(f"Unknown content scene: {scene}")
    root = Path(project_root).resolve() if project_root else PROJECT_ROOT
    assets = root / "assets/content"
    vendor = root / "assets/vendor/katex"
    source = (assets / f"{scene}.html").read_text(encoding="utf-8")
    if body_file:
        body_path = Path(body_file).resolve()
        body = _embed_body_resources(body_path.read_text(encoding="utf-8"), body_path.parent)
        source = re.sub(r"<!-- CONTENT_START -->.*?<!-- CONTENT_END -->", lambda _: "<!-- CONTENT_START -->\n" + body + "\n<!-- CONTENT_END -->", source, count=1, flags=re.S)
    css = _embed_css((vendor / "katex.min.css").read_text(encoding="utf-8"), vendor)
    css += "\n" + (assets / "shared.css").read_text(encoding="utf-8")
    font_faces = 1
    font_source = "custom" if font else "bundled-noto-sans-sc"
    if font:
        font_path = Path(font).resolve()
        formats = {".woff2": "woff2", ".woff": "woff", ".ttf": "truetype", ".otf": "opentype"}
        if font_path.suffix.lower() not in formats:
            raise ValueError("--font supports .woff2, .woff, .ttf, or .otf")
        css += ('\n@font-face{font-family:"ContentEmbeddedChinese";font-style:normal;font-weight:400;src:url("' + _data_url(font_path) + '") format("' + formats[font_path.suffix.lower()] + '");}\n:root{--content-font-zh:"ContentEmbeddedChinese",MiSans,"Microsoft YaHei","Noto Sans SC",system-ui,sans-serif;}')
    else:
        font_css, font_faces = _bundled_chinese_css(root / "assets/vendor/noto-sans-sc/font-bundle.json", source + (title or DEFAULT_TITLES[scene]) + (assets / "shared.js").read_text(encoding="utf-8"))
        css += "\n" + font_css
    katex = (vendor / "katex.min.js").read_text(encoding="utf-8")
    auto_render = (vendor / "contrib/auto-render.min.js").read_text(encoding="utf-8")
    math_script = (katex + "\n;\n" + auto_render).replace("</script", "<\\/script")
    shared_script = (assets / "shared.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    replacements = {
        "{{TITLE}}": escape(title or DEFAULT_TITLES[scene]),
        "{{STYLE}}": css,
        "{{MATH_SCRIPT}}": math_script,
        "{{SHARED_SCRIPT}}": shared_script,
        "{{LICENSE}}": escape((vendor / "LICENSE").read_text(encoding="utf-8") + ("\n\n" + (root / "assets/vendor/noto-sans-sc/LICENSE").read_text(encoding="utf-8") if not font else "")),
    }
    # One pass prevents trusted body text from accidentally expanding nested tokens.
    result = re.sub(r"\{\{(?:TITLE|STYLE|MATH_SCRIPT|SHARED_SCRIPT|LICENSE)\}\}", lambda m: replacements[m[0]], source)
    counter = _PageCounter()
    counter.feed(result)
    if scene in ("report", "rednote") and not counter.count:
        raise ValueError("Fixed-page scenes need explicit elements with data-export-page")
    destination = Path(output).resolve()
    if destination.suffix.lower() not in (".html", ".htm"):
        destination = destination / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result, encoding="utf-8")
    return {
        "scene": scene,
        "output": str(destination),
        "template_example": body_file is None,
        "explicit_pages": counter.count,
        "embedded_chinese_font": True,
        "chinese_font_source": font_source,
        "chinese_font_faces": font_faces,
        "bytes": destination.stat().st_size,
        "activate_hook": "activateContentExport" if scene == "report" else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=SCENES, required=True)
    parser.add_argument("--output", required=True, help="HTML file or directory (creates index.html)")
    parser.add_argument("--title", help="Document/first-page title")
    parser.add_argument("--body-file", help="Already-written trusted HTML fragment; fixed scenes must include data-export-page")
    parser.add_argument("--font", help="Local Chinese font you are permitted to embed (.woff2/.woff/.ttf/.otf); overrides downloaded Noto Sans SC fallback")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build_content_template(args.scene, args.output, title=args.title, body_file=args.body_file, font=args.font), ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

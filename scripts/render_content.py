#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check an already generated self-contained HTML and export explicitly marked content.

This tool performs browser/resource/layout checks, not technical or editorial validation.
It does not generate content, paginate articles, or call an image-generation service.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SCENES = ("learning", "blog", "report", "rednote", "diagram")
DEFAULT_VIEWPORTS = {
    "learning": (1440, 1000), "blog": (1440, 1000),
    "report": (1280, 720), "rednote": (1080, 1440), "diagram": (1440, 1000),
}
RESOURCE_TAGS = {
    "img": ("src",), "script": ("src",), "iframe": ("src",),
    "source": ("src",), "video": ("src", "poster"), "audio": ("src",),
    "embed": ("src",), "object": ("data",), "image": ("href", "xlink:href"),
    "use": ("href", "xlink:href"), "input": ("src",),
}
RESOURCE_LINK_RELS = {"stylesheet", "icon", "preload", "modulepreload", "prefetch", "manifest"}


def _self_contained_url(url: str) -> bool:
    return not url.strip() or url.strip().startswith("#") or urlsplit(url.strip()).scheme.lower() == "data"


def _png_dimensions(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if raw[:8] != bytes([137, 80, 78, 71, 13, 10, 26, 10]):
        raise ValueError("Browser output is not a PNG")
    return struct.unpack(">II", raw[16:24])


def _srcset_urls(value: str) -> list[str]:
    urls = []
    position = 0
    while position < len(value):
        while position < len(value) and (value[position].isspace() or value[position] == ","):
            position += 1
        start = position
        while position < len(value) and not value[position].isspace():
            position += 1
        url = value[start:position]
        if not url:
            break
        urls.append(url.rstrip(","))
        if url.endswith(","):
            continue
        while position < len(value) and value[position] != ",":
            position += 1
    return urls


def _css_resource_errors(css: str) -> list[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    urls = re.findall(r"url\(\s*([^)]*?)\s*\)", css, flags=re.I)
    urls += re.findall(r'@import\s+(?:"([^"]+)"|\'([^\']+)\')', css, flags=re.I)
    errors = []
    for item in urls:
        value = next((part for part in item if part), "") if isinstance(item, tuple) else item
        value = value.strip().strip("\"'")
        if not _self_contained_url(value):
            errors.append(f"Non-self-contained CSS resource: {value[:160]}")
    return errors


class _ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self.in_style = False
        self.css_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        for attr in RESOURCE_TAGS.get(tag, ()):
            value = values.get(attr, "")
            if value and not _self_contained_url(value):
                self.errors.append(f"Non-self-contained <{tag}> {attr}: {value[:160]}")
        if tag == "link" and RESOURCE_LINK_RELS.intersection(values.get("rel", "").lower().split()):
            if not _self_contained_url(values.get("href", "")):
                self.errors.append(f"Non-self-contained <link> resource: {values['href'][:160]}")
        if tag == "base" and values.get("href"):
            self.errors.append("<base href> is not supported in a portable self-contained HTML")
        # srcset parsing can contain commas inside data URLs. Require every candidate
        # to be embedded and let the browser decode the selected candidate.
        if "srcset" in values:
            candidates = _srcset_urls(values["srcset"])
            if any(not _self_contained_url(candidate) for candidate in candidates):
                self.errors.append(f"Non-self-contained srcset on <{tag}>")
        if "style" in values:
            self.errors.extend(_css_resource_errors(values["style"]))
        if tag == "style":
            self.in_style = True

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.css_parts.append(data)


def check_self_contained_html(html: str) -> list[str]:
    parser = _ResourceParser()
    parser.feed(html)
    parser.errors.extend(_css_resource_errors("".join(parser.css_parts)))
    return list(dict.fromkeys(parser.errors))


LAYOUT_AUDIT = r"""({selector, fixed, width, height, strictScroll=false}) => {
  const root = selector ? document.querySelector(selector) : document.documentElement;
  const errors = [];
  if (!root) return {errors:['Export target not found'], visible:false};
  const box = root.getBoundingClientRect();
  const visible = el => {
    for (let n=el; n && n.nodeType===1; n=n.parentElement) {
      const s=getComputedStyle(n);
      if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0) return false;
    }
    const r=el.getBoundingClientRect(); return r.width>0 && r.height>0;
  };
  if(!visible(root)) errors.push('Export target is hidden; supply an explicit --activate-hook');
  const tol=2;
  if(fixed && (Math.abs(box.width-width)>tol || Math.abs(box.height-height)>tol))
    errors.push('Target frame size '+box.width+'x'+box.height+' differs from '+width+'x'+height);
  if(!fixed && (document.documentElement.scrollWidth>innerWidth+tol || box.width>innerWidth+tol))
    errors.push('Document has horizontal overflow');
  if(fixed && (root.scrollWidth>root.clientWidth+tol || root.scrollHeight>root.clientHeight+tol))
    errors.push('Export target has width/height overflow');
  const describe = el => el.tagName.toLowerCase()+(el.id?'#'+el.id:'');
  const within=(a,b,x=true,y=true)=> (!x||(a.left>=b.left-tol&&a.right<=b.right+tol)) &&
    (!y||(a.top>=b.top-tol&&a.bottom<=b.bottom+tol));
  const checkRect=(r,el,label,includeSelf=false)=>{
    if(r.width<=0||r.height<=0)return;
    if(fixed && !within(r,box)) errors.push('Content exceeds export frame: '+label);
    for(let n=includeSelf?el:el.parentElement;n && n!==document.documentElement;n=n.parentElement){
      const s=getComputedStyle(n), nr=n.getBoundingClientRect();
      const clipModes=(fixed||strictScroll)?['hidden','clip','auto','scroll']:['hidden','clip'];
      const x=clipModes.includes(s.overflowX);
      const y=clipModes.includes(s.overflowY);
      if((x||y)&&!within(r,nr,x,y)) errors.push('Clipped/scrolling content in '+describe(n)+': '+label);
      if(n===root) break;
    }
  };
  // Audit mathematical outer boxes, never KaTeX's deliberately clipped internal SVG.
  for(const el of root.querySelectorAll('img,canvas,video,table,pre,svg,.katex')){
    if(!visible(el)||el.closest('.katex-mathml')||
      (el.tagName.toLowerCase()==='svg'&&el.closest('.katex')))continue;
    checkRect(el.getBoundingClientRect(),el,describe(el));
  }
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  for(let node=walker.nextNode();node;node=walker.nextNode()){
    const el=node.parentElement;
    if(!node.textContent.trim()||!el||!visible(el)||
      el.closest('script,style,svg,.katex,.sr-only,[aria-hidden="true"]'))continue;
    const range=document.createRange();range.selectNodeContents(node);
    for(const r of range.getClientRects())checkRect(r,el,'text in '+describe(el),true);
  }
  for(const text of root.querySelectorAll('svg text')){
    if(!visible(text)||text.closest('.katex'))continue;
    const svg=text.ownerSVGElement;
    if(svg&&!within(text.getBoundingClientRect(),svg.getBoundingClientRect()))
      errors.push('SVG label exceeds SVG viewport: '+text.textContent.slice(0,60));
  }
  return {visible:visible(root),box:{width:box.width,height:box.height},
    scrollWidth:root.scrollWidth,scrollHeight:root.scrollHeight,
    errors:[...new Set(errors)].slice(0,100)};
}"""


async def _ready(page: Any, timeout_ms: int) -> dict[str, Any]:
    async def wait() -> dict[str, Any]:
        return await page.evaluate(r"""async () => {
          if(window.__CONTENT_EXPORT_READY__) await window.__CONTENT_EXPORT_READY__;
          await document.fonts.ready;
          for(const image of document.images) image.loading='eager';
          const imageErrors=[];
          for(const image of document.images){
            try{await image.decode();}catch(e){imageErrors.push((image.currentSrc||image.src||'[empty image]').slice(0,160));}
            if(!image.complete||!image.naturalWidth)imageErrors.push((image.currentSrc||image.src||'[empty image]').slice(0,160));
          }
          for(const el of document.querySelectorAll('svg image')){
            const src=el.getAttribute('href')||el.getAttribute('xlink:href');
            if(src){try{const img=new Image();img.src=src;await img.decode();}catch(e){imageErrors.push(src.slice(0,160));}}
          }
          await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
          return {fonts:document.fonts.status,images:document.images.length,
            missingImages:[...new Set(imageErrors)],mathErrors:document.querySelectorAll('.katex-error,.MathJax_Error').length};
        }""")
    return await asyncio.wait_for(wait(), timeout=timeout_ms / 1000)


def _previous_generated_files(output_dir: Path) -> list[str]:
    """Only renderer-owned single filenames from QA are eligible for cleanup."""
    try:
        previous = json.loads((output_dir / "qa.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(previous, dict):
        return []
    names = set()
    for field in ("images", "retained_previous_images"):
        records = previous.get(field, [])
        if not isinstance(records, list):
            continue
        for record in records:
            name = record.get("file") if isinstance(record, dict) else None
            if isinstance(name, str) and re.fullmatch(r"(?:preview|page-[0-9]{2,})[.]png", name):
                if (output_dir / name).is_file() or (output_dir / name).is_symlink():
                    names.add(name)
    return sorted(names)


async def render_content(
    html_file: str | Path, output_dir: str | Path, *, scene: str = "learning",
    browser_executable: str | Path | None = None, selector: str | None = None,
    dpr: float = 1, width: int | None = None, height: int | None = None,
    export_images: bool = False, activate_hook: str | None = None,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    """Return and persist truthful QA; publish HTML/images only after all checks pass."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    previous_images = _previous_generated_files(out)
    qa: dict[str, Any] = {
        "schema_version": 1, "scene": scene, "passed": False,
        "html_sha256": None, "images": [], "errors": [], "checks": {},
        "semantic_validation": {"performed": False, "note": "Resource/layout checks do not verify technical meaning or visual readability."},
    }
    browser = None
    try:
        if scene not in SCENES:
            raise ValueError(f"scene must be one of {SCENES}")
        if not math.isfinite(dpr) or dpr <= 0:
            raise ValueError("dpr must be finite and positive")
        vw, vh = DEFAULT_VIEWPORTS[scene]
        vw, vh = vw if width is None else width, vh if height is None else height
        if vw <= 0 or vh <= 0 or timeout_ms <= 0:
            raise ValueError("width, height and timeout must be positive")
        if activate_hook and not re.fullmatch(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*", activate_hook):
            raise ValueError("--activate-hook must be a global function name, not JavaScript source")
        source = Path(html_file).resolve(strict=True)
        if source.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("Input must be an HTML file")
        raw = source.read_bytes()
        html = raw.decode("utf-8-sig")
        qa["source_sha256"] = hashlib.sha256(raw).hexdigest()
        qa["viewport"] = {"width": vw, "height": vh, "dpr": dpr}
        static_errors = check_self_contained_html(html)
        qa["checks"]["self_contained"] = {"passed": not static_errors, "errors": static_errors}
        if static_errors:
            raise ValueError("Input must be self-contained; embed local/HTTP resources. " + "; ".join(static_errors))
        from playwright.async_api import async_playwright
        with tempfile.TemporaryDirectory(prefix="content-render-") as tmp_name:
            staging = Path(tmp_name)
            async with async_playwright() as playwright:
                launch: dict[str, Any] = {"headless": True, "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]}
                if browser_executable:
                    launch["executable_path"] = str(Path(browser_executable).resolve(strict=True))
                browser = await playwright.chromium.launch(**launch)
                context = await browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=dpr, offline=True)
                page = await context.new_page()
                runtime_errors: list[str] = []
                resource_errors: list[str] = []
                qa["checks"]["runtime"] = {"passed": None, "errors": runtime_errors}
                qa["checks"]["resources"] = {"passed": None, "errors": resource_errors}
                page.on("pageerror", lambda error: runtime_errors.append(str(error)))
                page.on("console", lambda message: runtime_errors.append("console.error: " + message.text) if message.type == "error" else None)
                page.on("requestfailed", lambda request: resource_errors.append(f"Failed resource: {request.url[:160]} ({request.failure})"))
                page.on("websocket", lambda socket: resource_errors.append("External websocket: " + socket.url))
                async def route_resource(route: Any) -> None:
                    url = route.request.url
                    if url == source.as_uri() or url.startswith(("data:", "blob:")):
                        await route.continue_()
                    else:
                        resource_errors.append("Non-self-contained runtime resource: " + url[:160])
                        await route.abort()
                await context.route("**/*", route_resource)
                page.set_default_timeout(timeout_ms)

                async def prepare() -> dict[str, Any]:
                    await page.goto(source.as_uri(), wait_until="load", timeout=timeout_ms)
                    hide_ui = "[data-export-ui]{display:none!important}" if scene in {"report", "rednote", "diagram"} else ""
                    await page.add_style_tag(content=hide_ui+" *,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important;caret-color:transparent!important}")
                    ready = await _ready(page, timeout_ms)
                    if ready["missingImages"]:
                        resource_errors.extend("Missing/undecodable image: " + url for url in ready["missingImages"])
                    if ready["mathErrors"]:
                        runtime_errors.append("Rendered mathematical error nodes: " + str(ready["mathErrors"]))
                    return ready

                ready = await prepare()
                qa["checks"]["ready"] = ready
                qa["checks"]["export_ui"] = await page.evaluate("""() => {
                    const nodes=[...document.querySelectorAll('[data-export-ui]')];
                    return {marked:nodes.length,visible:nodes.filter(e=>{
                        const r=e.getBoundingClientRect(),s=getComputedStyle(e);
                        return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';
                    }).length};
                }""")
                records: list[dict[str, Any]] = []
                audits: list[dict[str, Any]] = []
                qa["checks"]["layout"] = audits
                paginated = scene in {"report", "rednote", "diagram"}
                if paginated:
                    target_selector = selector or ("[data-export-figure]" if scene == "diagram" else "[data-export-page]")
                    count = await page.locator(target_selector).count()
                    if not count:
                        raise ValueError(f"No explicit export targets matched {target_selector!r}; the renderer does not paginate long documents")
                    nested = await page.evaluate("(s)=>[...document.querySelectorAll(s)].some(e=>e.parentElement?.closest(s))", target_selector)
                    if nested:
                        raise ValueError("Nested export targets are ambiguous")
                    for index in range(count):
                        if index:
                            await prepare()
                        locator = page.locator(target_selector).nth(index)
                        if activate_hook:
                            await page.evaluate("""async ({hook,selector,index,scene}) => {
                              const fn=hook.split('.').reduce((o,k)=>o?.[k],globalThis);
                              if(typeof fn!=='function')throw new Error('Activation hook does not exist: '+hook);
                              await fn({index,scene,element:document.querySelectorAll(selector)[index]});
                            }""", {"hook": activate_hook, "selector": target_selector, "index": index, "scene": scene})
                        await locator.evaluate("""(el,{selector,index})=>{
                          document.querySelectorAll(selector).forEach((other,i)=>{if(i!==index)other.style.setProperty('display','none','important')});
                          for(let n=el;n;n=n.parentElement){n.style.setProperty('transform','none','important');n.style.setProperty('zoom','1','important')}
                        }""", {"selector": target_selector, "index": index})
                        # Use a unique temporary selector to audit this exact target.
                        await locator.evaluate("(el)=>el.setAttribute('data-render-current','true')")
                        selected = '[data-render-current="true"]'
                        active_ready = await _ready(page, timeout_ms)
                        resource_errors.extend("Missing/undecodable image: "+url for url in active_ready["missingImages"])
                        if active_ready["mathErrors"]:
                            runtime_errors.append("Rendered mathematical error nodes: "+str(active_ready["mathErrors"]))
                        bounds = await locator.bounding_box()
                        if not bounds:
                            raise ValueError("Export target is hidden; use --activate-hook with the template's activation API")
                        fixed = scene in {"report", "rednote"}
                        audit = await page.evaluate(LAYOUT_AUDIT, {"selector": selected, "fixed": fixed, "width": vw, "height": vh})
                        if scene == "diagram":
                            # A figure may have its own dimensions; all content must fit its bounds.
                            audit = await page.evaluate(LAYOUT_AUDIT, {"selector": selected, "fixed": True, "width": bounds["width"], "height": bounds["height"]})
                        audits.append(audit)
                        if audit["errors"]:
                            raise ValueError("; ".join(audit["errors"]))
                        filename = f"page-{index + 1:02d}.png"
                        await locator.screenshot(path=str(staging / filename), animations="disabled")
                        png_width, png_height = _png_dimensions(staging / filename)
                        records.append({"file": filename, "kind": "figure" if scene == "diagram" else "page",
                                        "width": png_width, "height": png_height})
                else:
                    if selector and await page.locator(selector).count() != 1:
                        raise ValueError("Continuous-document --selector must match exactly one element")
                    audit = await page.evaluate(LAYOUT_AUDIT, {"selector": selector, "fixed": False, "width": vw, "height": vh})
                    audits.append(audit)
                    if audit["errors"]:
                        raise ValueError("; ".join(audit["errors"]))
                    await page.screenshot(path=str(staging / "preview.png"), animations="disabled", full_page=False)
                    png_width, png_height = _png_dimensions(staging / "preview.png")
                    records.append({"file": "preview.png", "kind": "preview", "width": png_width, "height": png_height})
                    if export_images:
                        await page.add_style_tag(content="[data-export-ui]{display:none!important}")
                        full_audit = await page.evaluate(LAYOUT_AUDIT, {"selector": selector, "fixed": False, "strictScroll": True, "width": vw, "height": vh})
                        audits.append(full_audit)
                        if full_audit["errors"]:
                            raise ValueError("; ".join(full_audit["errors"]))
                        filename = "page-01.png"
                        if selector:
                            await page.locator(selector).screenshot(path=str(staging / filename), animations="disabled")
                        else:
                            await page.screenshot(path=str(staging / filename), animations="disabled", full_page=True)
                        png_width, png_height = _png_dimensions(staging / filename)
                        records.append({"file": filename, "kind": "full-document", "width": png_width, "height": png_height})
                qa["checks"]["layout"] = audits
                qa["checks"]["runtime"] = {"passed": not runtime_errors, "errors": runtime_errors}
                qa["checks"]["resources"] = {"passed": not resource_errors, "errors": resource_errors}
                if runtime_errors or resource_errors:
                    raise ValueError("; ".join(runtime_errors + resource_errors))
                await browser.close()
                browser = None
                # Preserve original self-contained bytes, including embedded assets and scripts.
                (out / "index.html").write_bytes(raw)
                for record in records:
                    shutil.copy2(staging / record["file"], out / record["file"])
                new_names = {record["file"] for record in records}
                for old_name in previous_images:
                    if old_name not in new_names:
                        (out / old_name).unlink(missing_ok=True)
                qa["images"] = records
                qa["html_sha256"] = hashlib.sha256((out / "index.html").read_bytes()).hexdigest()
                qa["passed"] = True
    except Exception as error:
        for check_name in ("runtime", "resources"):
            check = qa["checks"].get(check_name)
            if check is not None:
                check["passed"] = not check["errors"]
        qa["errors"].append(f"{type(error).__name__}: {error}")
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
        if not qa["passed"] and previous_images:
            qa["retained_previous_images"] = [{"file": name} for name in previous_images]
        (out / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return qa


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file", help="Already generated, self-contained UTF-8 HTML")
    parser.add_argument("--scene", choices=SCENES, default="learning")
    parser.add_argument("--output-dir", "-o", required=True)
    parser.add_argument("--browser-executable")
    parser.add_argument("--selector", help="Explicit export target selector; no automatic article slicing")
    parser.add_argument("--dpr", type=float, default=1)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--export-images", action="store_true", help="Also export the full learning/blog document; other scenes already export marked targets")
    parser.add_argument("--activate-hook", help="Global function called with {index,scene,element}; index is zero-based")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = vars(parser.parse_args(argv))
    qa = asyncio.run(render_content(**args))
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0 if qa["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

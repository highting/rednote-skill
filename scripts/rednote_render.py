#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
小红书卡片渲染脚本
将 Markdown 文件渲染为小红书风格的图片卡片，自动根据内容高度分页。

使用方法:
    python rednote_render.py <markdown_file> [options]

选项:
    --output-dir, -o     输出目录（默认为当前工作目录）
    --theme, -t          排版主题（默认: academic）
    --width, -w          图片宽度（默认 1080）
    --height             图片高度（默认 1440）
    --dpr                设备像素比（默认 2）
    --math               数学公式渲染（off 或 katex，默认读取 front matter）

可用主题:
    default, playful-geometric, neo-brutalism, botanical,
    professional, retro, terminal, sketch, minimalist, academic

依赖安装:
    pip install markdown pyyaml playwright
    playwright install chromium
"""

import argparse
import asyncio
import base64
import mimetypes
import os
import re
import shutil
import sys
import tempfile
from html import escape
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import url2pathname

try:
    import markdown
    import yaml
    from playwright.async_api import async_playwright
except ImportError as e:
    if __name__ == '__main__':
        print(f"缺少依赖: {e}")
        print("请运行: pip install markdown pyyaml playwright && playwright install chromium")
        sys.exit(1)
    raise


# ============================================================
# 路径常量
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = SCRIPT_DIR / "assets"
THEMES_DIR = ASSETS_DIR / "themes"
KATEX_DIR = ASSETS_DIR / "vendor" / "katex"

# ============================================================
# 渲染参数
# ============================================================

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1440
ACADEMIC_BACKGROUND = '#FAF9F5'
MI_SANS_STACK = "'MiSans', 'Microsoft YaHei', 'Source Han Sans CN', 'PingFang SC', sans-serif"
MATH_MODES = ('off', 'katex')
KATEX_VERSION = '0.16.11'
HTML_DOCUMENT_CSS = '''<style>
    .card-inner {
        --font-heading: 'Microsoft YaHei', 'Source Han Sans CN', sans-serif;
        --font-body: 'Microsoft YaHei', 'Source Han Sans CN', sans-serif;
        border: 0; border-radius: 0; box-shadow: none;
    }
    .cover-container { font-family: 'Microsoft YaHei', 'Source Han Sans CN', sans-serif; }
    .card-content img { display: block; max-width: 100%; height: auto; }
    .card-content .katex-display { overflow: visible; }
    .page-number { font-size: 24px; bottom: 14px; right: 50px; }
</style>'''

# 可用主题
AVAILABLE_THEMES = [
    'default',
    'playful-geometric',
    'neo-brutalism',
    'botanical',
    'professional',
    'retro',
    'terminal',
    'sketch',
    'minimalist',
    'academic',
]

# ============================================================
# 主题配色（按主题统一管理，消除原版中 cover/card 两处字典的重复）
# ============================================================

# 封面背景渐变（纵向，180deg）
COVER_BACKGROUNDS = {
    'default':             'linear-gradient(180deg, #f3f4f8 0%, #fdfdfc 100%)',
    'playful-geometric':   'linear-gradient(180deg, #8B5CF6 0%, #F472B6 100%)',
    'neo-brutalism':       'linear-gradient(180deg, #FF4757 0%, #FECA57 100%)',
    'botanical':           'linear-gradient(180deg, #8a9e8b 0%, #c4cfc0 100%)',
    'professional':        'linear-gradient(180deg, #dce3ed 0%, #fcfbf8 100%)',
    'retro':               'linear-gradient(180deg, #c49568 0%, #f0e0cc 100%)',
    'terminal':            'linear-gradient(180deg, #0d1117 0%, #161b22 100%)',
    'sketch':              'linear-gradient(180deg, #e0d8c8 0%, #f9f5ed 100%)',
    'minimalist':          'linear-gradient(180deg, #e8e8e5 0%, #fafaf8 100%)',
    'academic':            ACADEMIC_BACKGROUND,
}

# 正文卡片背景渐变（斜向，135deg）
CARD_BACKGROUNDS = {
    'default':             'linear-gradient(135deg, #f3f4f8 0%, #fafaf9 100%)',
    'playful-geometric':   'linear-gradient(135deg, #8B5CF6 0%, #F472B6 100%)',
    'neo-brutalism':       'linear-gradient(135deg, #FF4757 0%, #FECA57 100%)',
    'botanical':           'linear-gradient(135deg, #a3b5a4 0%, #dce1d6 100%)',
    'professional':        'linear-gradient(135deg, #e0e6f0 0%, #f8f7f5 100%)',
    'retro':               'linear-gradient(135deg, #d4a878 0%, #f2e8d8 100%)',
    'terminal':            'linear-gradient(135deg, #0d1117 0%, #11151c 100%)',
    'sketch':              'linear-gradient(135deg, #e5ddd0 0%, #f7f2e8 100%)',
    'minimalist':          'linear-gradient(135deg, #e8e8e5 0%, #f5f5f2 100%)',
    'academic':            ACADEMIC_BACKGROUND,
}

# 封面标题文字渐变
TITLE_GRADIENTS = {
    'default':             'linear-gradient(180deg, #1a1d22 0%, #3d4147 100%)',
    'playful-geometric':   'linear-gradient(180deg, #7C3AED 0%, #F472B6 100%)',
    'neo-brutalism':       'linear-gradient(180deg, #000000 0%, #FF4757 100%)',
    'botanical':           'linear-gradient(180deg, #3a4d3b 0%, #6b8b6c 100%)',
    'professional':        'linear-gradient(180deg, #141a24 0%, #1e4b8c 100%)',
    'retro':               'linear-gradient(180deg, #4a2810 0%, #b85c28 100%)',
    'terminal':            'linear-gradient(180deg, #3fb950 0%, #58a6ff 100%)',
    'sketch':              'linear-gradient(180deg, #3b3a38 0%, #787671 100%)',
    'minimalist':          'linear-gradient(180deg, #0a0a0a 0%, #2e2e2e 100%)',
    'academic':            'linear-gradient(180deg, #18263d 0%, #18263d 100%)',
}


# ============================================================
# Markdown 解析
# ============================================================

def parse_markdown_file(file_path: str) -> dict:
    """读取 .md 文件，返回 {'metadata': {...}, 'body': '...'}"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 YAML front matter（--- 包裹的元数据块）
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

    if yaml_match:
        try:
            metadata = yaml.safe_load(yaml_match.group(1))
            if metadata is None:
                metadata = {}
        except yaml.YAMLError as exc:
            raise ValueError(f'YAML front matter 解析失败: {exc}') from exc
        if not isinstance(metadata, dict):
            raise ValueError('YAML front matter 必须是键值映射，而不是列表或标量')
        body = content[yaml_match.end():]
    else:
        metadata = {}
        body = content

    return {'metadata': metadata, 'body': body.strip()}


# ============================================================
# Markdown → HTML 转换
# ============================================================

def _collapse_display_math_lines(md_content: str) -> str:
    """压平 display math 内的换行，避免 nl2br 插入 <br> 打断 KaTeX 分隔符。"""
    def collapse(match):
        content = re.sub(r'\s*\n\s*', ' ', match.group(1)).strip()
        return f'{match.group(0)[0:2]}{content}{match.group(0)[-2:]}'

    md_content = re.sub(r'\\\[(.*?)\\\]', collapse, md_content, flags=re.DOTALL)
    return re.sub(r'\$\$(.*?)\$\$', collapse, md_content, flags=re.DOTALL)


def _stash_math(md_content: str) -> tuple:
    """暂存公式；代码示例保持原文，不参与公式预处理。"""
    blocks = []
    prefix = 'REDNOTEMATHPLACEHOLDER'
    while prefix in md_content:
        prefix += 'X'

    def stash(match):
        if match.group('math') is None:
            return match.group(0)
        token = f'{prefix}{len(blocks)}END'
        blocks.append((token, _collapse_display_math_lines(match.group(0))))
        return token

    protected = re.sub(
        r'^[ \t]{0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n.*?'
        r'^[ \t]{0,3}(?P=fence)[ \t]*(?=\n|\Z)'
        r'|(?P<ticks>`+)[^`]*?(?P=ticks)'
        r'|<(?P<code_tag>pre|code)\b[^>]*>.*?</(?P=code_tag)>'
        r'|(?P<math>\\\(.*?\\\)|\\\[.*?\\\]|\$\$.*?\$\$)',
        stash,
        md_content,
        flags=re.DOTALL | re.MULTILINE,
    )
    return protected, blocks


def convert_markdown_to_html(md_content: str, math_mode: str = 'off') -> str:
    """将 Markdown 正文转为 HTML，自动识别文末 #tag 并渲染为标签"""
    # 提取文末的 #标签 行（例如 "#Python #AI #教程"）
    md_content = md_content.rstrip()
    tags_match = re.search(
        r'(?:^|\n)((?:#[\w\u4e00-\u9fff]+\s*)+)$',
        md_content,
    )
    tags_html = ""

    if tags_match:
        tags_str = tags_match.group(1)
        md_content = md_content[:tags_match.start(1)].rstrip()
        tags = re.findall(r'#([\w一-龥]+)', tags_str)
        if tags:
            parts = ['<div class="tags-container">']
            for tag in tags:
                parts.append(f'<span class="tag">#{escape(tag)}</span>')
            parts.append('</div>')
            tags_html = ''.join(parts)

    math_blocks = []
    if math_mode == 'katex':
        md_content, math_blocks = _stash_math(md_content)

    html = markdown.markdown(
        md_content,
        extensions=['extra', 'codehilite', 'tables', 'nl2br'],
    )
    for token, formula in math_blocks:
        html = html.replace(token, escape(formula, quote=False))
    return html + tags_html


# ============================================================
# 主题 CSS 加载
# ============================================================

def load_theme_css(theme: str) -> str:
    """从 assets/themes/{theme}.css 读取主题样式，fallback 到 default.css"""
    theme_file = THEMES_DIR / f"{theme}.css"
    if theme_file.exists():
        with open(theme_file, 'r', encoding='utf-8') as f:
            return f.read()

    default_file = THEMES_DIR / "default.css"
    if default_file.exists():
        with open(default_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def _normalize_render_options(metadata: dict,
                              math_override: Optional[str] = None) -> dict:
    """规范化渲染选项，确保分页测量和最终渲染使用同一配置。"""
    if not isinstance(metadata, dict):
        raise ValueError('渲染元数据必须是键值映射')
    raw_math = math_override if math_override is not None else metadata.get('math', 'off')
    if raw_math is None or raw_math is False:
        raw_math = 'off'
    math_mode = str(raw_math).strip().lower()
    if math_mode not in MATH_MODES:
        raise ValueError(
            f"不支持的数学公式模式: {raw_math!r}，可选值为: {', '.join(MATH_MODES)}"
        )
    return {'math_mode': math_mode}


def _escaped_metadata_value(metadata: dict, key: str, default: str = '') -> str:
    """读取并转义 front matter 文本，避免破坏封面 HTML。"""
    value = metadata.get(key, default)
    if value is None:
        value = default
    return escape(str(value))


def _katex_assets(math_mode: str) -> tuple:
    """返回本地 KaTeX 资源和初始化脚本。"""
    if math_mode != 'katex':
        return '', ''

    css_path = KATEX_DIR / 'katex.min.css'
    js_path = KATEX_DIR / 'katex.min.js'
    auto_render_path = KATEX_DIR / 'contrib' / 'auto-render.min.js'
    missing = [path for path in (css_path, js_path, auto_render_path) if not path.exists()]
    if missing:
        paths = ', '.join(str(path) for path in missing)
        raise FileNotFoundError(f'缺少 KaTeX 本地资源: {paths}')

    head = f'''        <link rel="stylesheet" href="{css_path.as_uri()}" data-katex-version="{KATEX_VERSION}">
        <script defer src="{js_path.as_uri()}"></script>
        <script defer src="{auto_render_path.as_uri()}"></script>'''
    script = r'''<script>
        window.__REDNOTE_MATH_READY__ = 'pending';
        window.__REDNOTE_MATH_ERROR__ = false;
        window.addEventListener('DOMContentLoaded', function () {
            try {
                if (typeof window.renderMathInElement !== 'function') {
                    throw new Error('本地 KaTeX 未加载');
                }
                window.renderMathInElement(document.body, {
                    delimiters: [
                        {left: '\\(', right: '\\)', display: false},
                        {left: '\\[', right: '\\]', display: true},
                        {left: '$$', right: '$$', display: true}
                    ],
                    throwOnError: false,
                    errorCallback: function () {
                        window.__REDNOTE_MATH_ERROR__ = true;
                    }
                });
                window.__REDNOTE_MATH_READY__ = 'ready';
            } catch (error) {
                window.__REDNOTE_MATH_ERROR__ = true;
                window.__REDNOTE_MATH_READY__ = 'unavailable';
            }
        });
    </script>'''
    return head, script


# ============================================================
# HTML 生成
# ============================================================

def generate_cover_html(metadata: dict, theme: str, width: int, height: int) -> str:
    """生成封面页 HTML——标题使用固定字号，超长时自动换行而非缩小"""
    default_emoji = '' if theme == 'academic' else '📝'
    emoji = _escaped_metadata_value(metadata, 'emoji', default_emoji)
    title = _escaped_metadata_value(metadata, 'title', '标题')
    subtitle = _escaped_metadata_value(metadata, 'subtitle')

    # 固定标题字号，让长标题自然换行
    title_size = int(width * (0.075 if theme == 'academic' else 0.095))
    subtitle_size = int(width * (0.045 if theme == 'academic' else 0.067))

    bg = COVER_BACKGROUNDS.get(theme, COVER_BACKGROUNDS['default'])
    title_gradient = TITLE_GRADIENTS.get(theme, TITLE_GRADIENTS['default'])
    if theme == 'academic':
        title_paint = 'color: #2F2D29;'
    else:
        title_paint = f'''background: {title_gradient};
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;'''

    font_stack = (
        "'Cambria', 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', 'SimSun', serif"
        if theme == 'academic' else MI_SANS_STACK
    )
    # 所有尺寸按比例计算，保证不同 width/height 下版面一致
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width={width}, height={height}">
    <title>小红书封面</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: {font_stack};
            width: {width}px;
            height: {height}px;
            overflow: hidden;
        }}

        .cover-container {{
            width: {width}px;
            height: {height}px;
            background: {bg};
            position: relative;
            overflow: hidden;
        }}

        .cover-inner {{
            position: absolute;
            width: {int(width * 0.88)}px;
            height: {int(height * 0.91)}px;
            left: {int(width * 0.06)}px;
            top: {int(height * 0.045)}px;
            background: {ACADEMIC_BACKGROUND if theme == 'academic' else '#F3F3F3'};
            border-radius: {0 if theme == 'academic' else 25}px;
            display: flex;
            flex-direction: column;
            padding: {int(width * 0.074)}px {int(width * 0.079)}px;
            overflow: hidden;
        }}

        .cover-emoji {{
            font-size: {int(width * 0.167)}px;
            line-height: 1.2;
            margin-bottom: {int(height * 0.035)}px;
            flex-shrink: 0;
        }}

        .cover-emoji:empty {{ display: none; }}

        .cover-title {{
            font-weight: 900;
            font-size: {title_size}px;
            line-height: 1.35;
            {title_paint}
            flex: 1 1 auto;
            min-height: 0;
            overflow: hidden;
            overflow-wrap: break-word;
            word-break: normal;
        }}

        .cover-subtitle {{
            font-weight: 350;
            font-size: {subtitle_size}px;
            line-height: 1.4;
            color: #000000;
            margin-top: auto;
            flex-shrink: 0;
        }}
    </style>
</head>
<body>
    <div class="cover-container">
        <div class="cover-inner">
            <div class="cover-emoji">{emoji}</div>
            <div class="cover-title">{title}</div>
            <div class="cover-subtitle">{subtitle}</div>
        </div>
    </div>
</body>
</html>'''


def generate_card_html(content: str, theme: str, page_number: int,
                       total_pages: int, width: int, height: int,
                       math_mode: str = 'off', extra_head: str = '') -> str:
    """生成一张小红书正文卡片 HTML。"""
    html_body = convert_markdown_to_html(content, math_mode)
    theme_css = load_theme_css(theme)
    bg = CARD_BACKGROUNDS.get(theme, CARD_BACKGROUNDS['default'])
    page_text = f"{page_number}/{total_pages}" if total_pages > 1 else ""
    page_markup = f'<div class="page-number">{page_text}</div>'
    katex_head, katex_script = _katex_assets(math_mode)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width={width}">
    <title>小红书卡片</title>
    {katex_head}
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: {MI_SANS_STACK};
            width: {width}px;
            background: transparent;
        }}

        .card-container {{
            width: {width}px;
            min-height: {height}px;
            background: {bg};
            position: relative;
            padding: 50px;
            overflow: hidden;
        }}

        .card-inner {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 60px;
            min-height: calc({height}px - 100px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }}

        .card-content {{
            line-height: 1.7;
        }}

        .card-content :not(pre) > code {{
            overflow-wrap: anywhere;
            word-break: break-word;
        }}

        .card-content table {{
            display: block;
            width: 100%;
            max-width: 100%;
            overflow-x: auto;
            border-collapse: collapse;
            font-size: 0.82em;
        }}

        .card-content th,
        .card-content td {{
            padding: 0.35em 0.55em;
            border: 1px solid #cbd5e1;
            text-align: left;
            overflow-wrap: anywhere;
        }}

        .card-content th {{ font-weight: 700; }}

        .card-content > svg,
        .card-content .figure-panel > svg,
        .card-content .figure-grid > svg,
        .card-content .figure-flow > svg {{
            display: block;
            width: auto;
            max-width: 100%;
            height: auto;
            margin: 36px auto;
        }}

        .card-content .katex-display {{
            max-width: 100%;
            overflow-x: auto;
            overflow-y: hidden;
            padding: 0.2em 0;
        }}

        .card-content .katex {{ font-size: 1em; }}

        .page-number {{
            position: absolute;
            bottom: 80px;
            right: 80px;
            font-size: 36px;
            color: rgba(255, 255, 255, 0.8);
            font-weight: 500;
        }}

        {theme_css}

        /* 主题只用 ::marker 着色，恢复有序列表的数字标记 */
        .card-content ol {{ list-style: decimal; }}
    </style>
    {extra_head}
</head>
<body>
    <div class="card-container">
        <div class="card-inner">
            <div class="card-content">{html_body}</div>
        </div>
        {page_markup}
    </div>
</body>
{katex_script}
</html>'''


# ============================================================
# 渲染引擎
# ============================================================

def _validate_dimensions(width: int, height: int, dpr: int) -> None:
    """校验浏览器视口和设备像素比，尽早给出可读错误。"""
    if width <= 0 or height <= 0:
        raise ValueError('width 和 height 必须是正整数')
    if dpr <= 0:
        raise ValueError('dpr 必须是正整数')

async def _wait_for_renderers(page, math_mode: str = 'off'):
    """等待本地样式、字体和可选公式渲染器完成。"""
    await page.wait_for_load_state('domcontentloaded')
    if math_mode == 'katex':
        await page.wait_for_function(
            "() => ['ready', 'unavailable'].includes(window.__REDNOTE_MATH_READY__)",
            timeout=5000,
        )
        if await page.evaluate(
            "window.__REDNOTE_MATH_READY__ !== 'ready' "
            "|| window.__REDNOTE_MATH_ERROR__ "
            "|| !!document.querySelector('.katex-error')"
        ):
            raise ValueError('公式渲染失败，请检查 LaTeX 和本地 KaTeX 资源')
    # 公式排版会触发额外的数学字体加载；必须在排版之后等待字体。
    await page.evaluate('document.fonts.ready')
    if not await page.evaluate('''async () => {
        await Promise.all(Array.from(document.images, image =>
            image.decode().catch(() => null)));
        return Array.from(document.images).every(image => image.naturalWidth > 0);
    }'''):
        raise ValueError('图片加载失败，请检查图片路径与文件')


async def _check_canvas_bounds(page, width: int, height: int) -> None:
    """固定画幅检查；KaTeX 的内部纵向排版差异不作为溢出。"""
    overflow = await page.evaluate('''({width, height}) => {
        const root = document.querySelector('.card-container, .cover-container');
        const checks = document.querySelectorAll(
            '.card-content, .katex-display, table, .cover-title, .cover-subtitle');
        return root.scrollHeight > height || root.scrollWidth > width ||
            Array.from(checks).some(el =>
                el.scrollWidth > el.clientWidth + 1 ||
                (!el.classList.contains('katex-display') &&
                 el.scrollHeight > el.clientHeight + 1));
    }''', {'width': width, 'height': height})
    if overflow:
        raise ValueError('内容超出固定画幅，请拆分过高块或调整公式换行后重试')


async def render_html_to_png(html: str, output_path: str,
                             width: int, height: int, dpr: int,
                             math_mode: str = 'off') -> int:
    """将 HTML 渲染为 PNG 图片，返回实际图片高度"""
    _validate_dimensions(width, height, dpr)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            # 视口高度给足够余量（3 倍卡片高度），内容超出时 scrollHeight 仍然准确
            page = await browser.new_page(
                viewport={'width': width, 'height': height * 3},
                device_scale_factor=dpr,
            )

            # 写入临时文件后通过 file:// 加载，比 set_content 更稳定
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.html', delete=False, encoding='utf-8'
                ) as f:
                    f.write(html)
                    temp_path = f.name

                await page.goto(Path(temp_path).as_uri(), wait_until='domcontentloaded')
                await _wait_for_renderers(page, math_mode)

                await _check_canvas_bounds(page, width, height)

                await page.screenshot(
                    path=output_path,
                    clip={'x': 0, 'y': 0, 'width': width, 'height': height},
                    type='png',
                )

                print(f"  ✅ 已生成: {output_path} ({width}x{height})")
                return height
            finally:
                if temp_path:
                    try:
                        os.unlink(temp_path)
                    except FileNotFoundError:
                        pass
                await page.close()
        finally:
            await browser.close()


# ============================================================
# 自动分页
# ============================================================

async def measure_card_height(page, md_content: str, theme: str,
                              width: int, height: int,
                              math_mode: str = 'off', extra_head: str = '') -> float:
    """生成临时卡片 HTML 并测量 .card-content 的实际渲染高度"""
    html = generate_card_html(md_content, theme, 1, 1, width, height, math_mode, extra_head)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False, encoding='utf-8'
        ) as f:
            f.write(html)
            temp_path = f.name

        await page.goto(Path(temp_path).as_uri(), wait_until='domcontentloaded')
        await _wait_for_renderers(page, math_mode)

        return await page.evaluate('''() => {
            const content = document.querySelector('.card-content');
            return content ? content.scrollHeight : 0;
        }''')
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def _split_body_to_sentences(text: str) -> list:
    """按中英文标点切句，保留分隔空白以便无损重组。"""
    sentences = re.split(r'(?<=[。！？；\n])|(?<=[.!?;])(?=\s)', text)
    result = []
    for sentence in sentences:
        if not sentence:
            continue
        while len(sentence) > 240:
            # 只在已有空白处拆自然语言；连续 URL 等保持为完整单元。
            boundaries = list(re.finditer(r'\s+', sentence[:240]))
            if not boundaries or boundaries[-1].start() == 0:
                break
            end = boundaries[-1].end()
            result.append(sentence[:end])
            sentence = sentence[end:]
        result.append(sentence)
    return result


def _is_atomic_block(text: str) -> bool:
    """判断代码块、表格和 SVG 是否应作为一个不可拆分的 Markdown 块。"""
    stripped = text.strip()
    if re.match(r'^(?:`{3,}|~{3,}|\\\[|\$\$)', stripped):
        return True
    if re.match(r'^(?:[-+*]\s|\d+[.)]\s|>\s)', stripped):
        return True
    if re.match(r'^<svg\b', stripped, re.IGNORECASE) and re.search(
        r'</svg>\s*$', stripped, re.IGNORECASE
    ):
        return True
    if re.match(r'^<div\b', stripped, re.IGNORECASE) and re.search(
        r'</div>\s*$', stripped, re.IGNORECASE
    ):
        return True
    lines = stripped.splitlines()
    return (
        len(lines) >= 2
        and '|' in lines[0]
        and bool(re.match(r'^\s*\|?\s*:?-{3,}', lines[1]))
    )


def _split_body_to_paragraphs(body: str) -> list:
    """按空行切分正文，同时保留代码块和 SVG 内部的空行。"""
    lines = body.splitlines()
    paragraphs = []
    current = []
    fence = None
    math_end = None
    in_svg = False
    html_depth = 0

    def flush() -> None:
        if current:
            paragraph = '\n'.join(current).strip()
            if paragraph:
                paragraphs.append(paragraph)
            current.clear()

    for line in lines:
        stripped = line.strip()
        if fence is not None:
            current.append(line)
            if re.fullmatch(re.escape(fence[0]) + '{' + str(len(fence)) + ',}', stripped):
                fence = None
            continue
        fence_match = re.match(r'^(`{3,}|~{3,})', stripped)
        if fence_match:
            fence = fence_match.group(1)
            current.append(line)
            continue
        if math_end:
            current.append(line)
            if math_end in stripped:
                math_end = None
            continue
        for opener, closer in ((r'\[', r'\]'), ('$$', '$$')):
            if stripped.startswith(opener) and closer not in stripped[len(opener):]:
                math_end = closer
        if re.match(r'^<svg\b', stripped, re.IGNORECASE):
            in_svg = True
        html_depth += len(re.findall(r'<div\b[^>]*>', stripped, re.IGNORECASE))
        html_depth -= len(re.findall(r'</div\s*>', stripped, re.IGNORECASE))
        html_depth = max(0, html_depth)
        current.append(line)
        if in_svg and re.search(r'</svg>\s*$', stripped, re.IGNORECASE):
            in_svg = False
        if not stripped and not math_end and not in_svg and html_depth == 0:
            flush()

    flush()
    return paragraphs


def _split_para_to_sentences(para: str) -> list:
    """将段落按句子切分。如果以 markdown 标题开头，标题独立不拆分"""
    if _is_atomic_block(para):
        return [para]
    heading_match = re.match(r'^(#{1,6}\s[^\n]*)(\n|$)', para)
    if heading_match:
        heading = heading_match.group(1)
        rest = para[heading_match.end():].strip()
        if rest:
            return [heading] + _split_body_to_sentences(rest)
        return [heading]
    return _split_body_to_sentences(para)


def _is_heading(text: str) -> bool:
    """判断文本块是否为 markdown 标题行（以 # 开头）"""
    return bool(re.fullmatch(r'#{1,6}[ \t]+[^\n]+', text.strip()))


def _join_sentences(sentences: list) -> str:
    """拼接句子列表，标题后自动补换行，避免标题吞掉正文"""
    parts = []
    for s in sentences:
        parts.append(s)
        if _is_heading(s):
            parts.append('\n')
    return ''.join(parts)


async def _fit_sentences(page, sentences: list, base_md: str,
                         available_height: int, theme: str,
                         width: int, height: int,
                         math_mode: str = 'off', extra_head: str = '') -> tuple:
    """
    在 base_md 基础上，逐句追加 sentences，返回 (可塞入的句子, 剩余句子)。
    不会让标题单独留在卡片末尾（heading orphan 保护）。
    """
    fit_count = 0
    for _ in sentences:
        extra = _join_sentences(sentences[:fit_count + 1])
        test_md = base_md + '\n\n' + extra if base_md else extra
        test_h = await measure_card_height(
            page, test_md, theme, width, height, math_mode, extra_head
        )
        if test_h > available_height:
            break
        fit_count += 1

    # 末尾不留下孤立的标题 —— 把它推到下一张卡片
    while fit_count > 0 and _is_heading(sentences[fit_count - 1]):
        fit_count -= 1

    return sentences[:fit_count], sentences[fit_count:]


async def auto_split_body(body: str, theme: str, width: int, height: int,
                          dpr: int, math_mode: str = 'off', extra_head: str = '') -> list:
    """
    按段落累加分页。段落超出时先按句子切分尽量塞入，剩余句子作为新段落回填。
    保证标题不会孤零零地挂在卡片底部。

    可用空间 = 卡片高度 - 220px
    """
    _validate_dimensions(width, height, dpr)
    paragraphs = _split_body_to_paragraphs(body)
    available_height = max(1, height - 220)
    cards = []
    current_paras = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={'width': width, 'height': height * 2},
            device_scale_factor=dpr,
        )

        try:
            idx = 0
            while idx < len(paragraphs):
                para = paragraphs[idx]

                # 尝试整段加入
                candidate_md = '\n\n'.join(current_paras + [para])
                h = await measure_card_height(
                    page, candidate_md, theme, width, height, math_mode, extra_head
                )

                if h <= available_height:
                    current_paras.append(para)
                else:
                    # 超出 → 拆句
                    sentences = _split_para_to_sentences(para)
                    base = '\n\n'.join(current_paras)
                    fitted, remaining = await _fit_sentences(
                        page, sentences, base, available_height, theme, width, height,
                        math_mode, extra_head,
                    )

                    if fitted:
                        current_paras.append(_join_sentences(fitted))

                    # 检查整张卡片末尾是否挂着标题
                    while current_paras and _is_heading(current_paras[-1]):
                        orphan = current_paras.pop()
                        remaining.insert(0, orphan)

                    # 单个原子块无法塞入空卡片时也必须前进，允许该卡片超出目标高度，
                    # 避免超长 URL、代码或 SVG 让分页循环永不结束。
                    if not fitted and not current_paras and remaining:
                        cards.append(_join_sentences(remaining))
                        idx += 1
                        continue

                    if current_paras:
                        cards.append('\n\n'.join(current_paras))

                    # 剩余句子回填到段落队列
                    current_paras = []
                    if remaining:
                        paragraphs.insert(idx + 1, _join_sentences(remaining))

                idx += 1

            if current_paras:
                cards.append('\n\n'.join(current_paras))

        finally:
            await browser.close()

    return cards


# ============================================================
# 主编排函数
# ============================================================

async def export_html_document(documents: list, output_dir: str,
                               width: int, height: int, math_mode: str) -> None:
    """保存实际排版后的页面和滚动入口；数学保持 DOM，资源可随目录移动。"""
    output = Path(output_dir).resolve()
    rendered = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page(viewport={'width': width, 'height': height})
            for filename, html, is_cover in documents:
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.html', delete=False, encoding='utf-8'
                ) as file:
                    file.write(html)
                    temporary = Path(file.name)
                try:
                    await page.goto(temporary.as_uri())
                    await _wait_for_renderers(page, 'off' if is_cover else math_mode)
                    await _check_canvas_bounds(page, width, height)
                    for img in await page.locator('img').all():
                        src = await img.evaluate('(el) => el.currentSrc || el.src')
                        if src.startswith('data:'):
                            continue
                        parsed = urlparse(src)
                        if parsed.scheme != 'file' or parsed.netloc not in ('', 'localhost'):
                            raise ValueError('HTML 导出需要本地图片或 data URI，请先本地化远程图片')
                        image_path = Path(url2pathname(parsed.path))
                        mime = mimetypes.guess_type(image_path.name)[0] or 'application/octet-stream'
                        encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
                        await img.evaluate('(el, src) => { el.src = src; el.removeAttribute("srcset"); }',
                                           f'data:{mime};base64,{encoded}')
                    # 保存已渲染的 KaTeX DOM；离线打开不再运行公式脚本。
                    await page.evaluate('''() => {
                        document.querySelectorAll('script, base').forEach(el => el.remove());
                        document.querySelectorAll('link[data-katex-version]').forEach(el =>
                            el.setAttribute('href', '../assets/katex/katex.min.css'));
                    }''')
                    rendered.append((filename, await page.content()))
                finally:
                    temporary.unlink(missing_ok=True)
        finally:
            await browser.close()

    pages_dir = output / 'pages'
    pages_dir.mkdir(parents=True, exist_ok=True)
    if math_mode == 'katex':
        shutil.copytree(KATEX_DIR, output / 'assets' / 'katex', dirs_exist_ok=True)
    for filename, html in rendered:
        (pages_dir / filename).write_text(html, encoding='utf-8')
    frames = '\n'.join(
        f'<section id="page-{index}"><iframe title="第 {index} 页" '
        f'src="pages/{filename}" width="{width}" height="{height}"></iframe></section>'
        for index, (filename, _) in enumerate(rendered, 1)
    )
    index_html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小红书分页技术文档</title>
<style>
body {{ margin: 0; background: #F3F1E9; }}
main {{ width: {width}px; margin: 0 auto; padding: 24px 0; }}
section {{ margin-bottom: 24px; width: {width}px; height: {height}px; }}
iframe {{ display: block; border: 0; background: {ACADEMIC_BACKGROUND}; }}
</style></head><body><main>{frames}</main></body></html>'''
    (output / 'index.html').write_text(index_html, encoding='utf-8')
    print(f'  已生成分页 HTML: {output / "index.html"}')


async def render_markdown_to_cards(
    md_file: str,
    output_dir: str,
    theme: str = 'academic',
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    dpr: int = 2,
    math_mode: Optional[str] = None,
    output_format: str = 'png',
    save_html: bool = False,
) -> int:
    """HTML＋SVG 分页并输出 PNG；可另存 HTML 制作源文件。"""
    _validate_dimensions(width, height, dpr)
    if theme not in AVAILABLE_THEMES:
        raise ValueError(
            f"不支持的主题: {theme!r}，可选值为: {', '.join(AVAILABLE_THEMES)}"
        )
    if output_format not in ('png', 'html'):
        raise ValueError('output_format 必须为 png 或 html')
    # 1. 解析文件
    data = parse_markdown_file(md_file)
    metadata = data['metadata']
    body = data['body']
    render_options = _normalize_render_options(metadata, math_mode)
    source_base = Path(md_file).resolve().parent.as_uri() + '/'
    extra_head = f'<base href="{escape(source_base, quote=True)}">'
    if theme == 'academic':
        extra_head += HTML_DOCUMENT_CSS
    print(f"\n🎨 开始渲染: {md_file}")
    print(f"  📐 主题: {theme}")
    print(f"  📐 尺寸: {width}x{height}")
    os.makedirs(output_dir, exist_ok=True)

    # 2. 自动分页
    print("  ⏳ 分析内容并自动分页...")
    card_contents = await auto_split_body(
        body, theme, width, height, dpr, render_options['math_mode'], extra_head
    )
    total_cards = len(card_contents)
    print(f"  📄 共 {total_cards} 张正文卡片")

    documents = []
    if metadata.get('emoji') or metadata.get('title'):
        cover = generate_cover_html(metadata, theme, width, height)
        documents.append(('cover.html', cover.replace('</head>', extra_head + '</head>'), True))
    documents.extend(
        (f'card_{index}.html', generate_card_html(
            content, theme, index, total_cards, width, height,
            render_options['math_mode'], extra_head), False)
        for index, content in enumerate(card_contents, 1)
    )
    if output_format == 'html':
        await export_html_document(documents, output_dir, width, height, render_options['math_mode'])
        return total_cards

    for filename, html, is_cover in documents:
        card_path = str(Path(output_dir) / Path(filename).with_suffix('.png'))
        await render_html_to_png(
            html, card_path, width, height, dpr,
            'off' if is_cover else render_options['math_mode'],
        )
    if save_html:
        await export_html_document(
            documents, str(Path(output_dir) / 'html'), width, height, render_options['math_mode']
        )

    print(f"\n✨ 渲染完成！图片已保存到: {output_dir}")
    return total_cards


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='通过 HTML＋SVG 分页生成小红书 PNG 图片，默认 academic 主题',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
可用主题:
  default             - 默认风格
  playful-geometric   - 活泼几何风格（Memphis 设计）
  neo-brutalism       - 新粗野主义风格
  botanical           - 植物园自然风格
  professional        - 专业商务风格
  retro               - 复古怀旧风格
  terminal            - 终端/命令行风格
  sketch              - 手绘素描风格（显式选择）
  minimalist          - 极简现代风格
  academic            - 默认技术风格（浅暖米色底 + 单一学术蓝，橙色仅作必要对照）
''',
    )
    parser.add_argument('markdown_file', help='Markdown 文件路径')
    parser.add_argument('--output-dir', '-o', default=os.getcwd(),
                        help='输出目录（默认为当前工作目录）')
    parser.add_argument('--theme', '-t', choices=AVAILABLE_THEMES,
                        default='academic', help='排版主题（默认: academic；其他主题按需指定）')
    parser.add_argument('--width', '-w', type=int, default=DEFAULT_WIDTH,
                        help=f'图片宽度（默认: {DEFAULT_WIDTH}）')
    parser.add_argument('--height', type=int, default=DEFAULT_HEIGHT,
                        help=f'图片高度（默认: {DEFAULT_HEIGHT}）')
    parser.add_argument('--dpr', type=int, default=2,
                        help='设备像素比（默认: 2）')
    parser.add_argument('--math', choices=MATH_MODES, default=None,
                        help='数学公式渲染（默认读取 front matter.math）')
    parser.add_argument('--format', choices=('png', 'html'), default='png',
                        help='默认 png；html 仅导出中间源文件，不完成小红书图片交付')
    parser.add_argument('--save-html', action='store_true',
                        help='输出 PNG 的同时在 html/ 保存可复用的页面源文件')

    args = parser.parse_args()

    if not os.path.exists(args.markdown_file):
        print(f"❌ 错误: 文件不存在 - {args.markdown_file}")
        sys.exit(1)

    try:
        asyncio.run(render_markdown_to_cards(
            md_file=args.markdown_file,
            output_dir=args.output_dir,
            theme=args.theme,
            width=args.width,
            height=args.height,
            dpr=args.dpr,
            math_mode=args.math,
            output_format=args.format,
            save_html=args.save_html,
        ))
    except (OSError, ValueError) as exc:
        print(f"❌ 错误: {exc}")
        sys.exit(2)


if __name__ == '__main__':
    main()

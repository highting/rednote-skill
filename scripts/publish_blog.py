"""将已检查的本地成品汇总到 output/<短名>/，原有交付先留存。"""

import argparse
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def publish_blog(run_dir: str, project_root: Path = PROJECT_ROOT) -> dict:
    output = project_root.resolve() / 'output'
    run = Path(run_dir).resolve()
    if not run.is_relative_to(output):
        raise ValueError('工作目录必须位于本项目 output/ 内')
    manifest_path = run / 'run.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['status'] != 'completed':
        raise ValueError('完成图片与配文检查并标记 completed 后，才能整理交付')
    artifacts = Path(manifest['artifact_dir']).resolve()
    destination = Path(manifest['delivery_dir']).resolve()
    if not artifacts.is_relative_to(run) or artifacts == run:
        raise ValueError('成品暂存目录必须位于本次工作目录内')
    if destination.parent != output or destination.name.startswith('_'):
        raise ValueError('交付目录必须是 output/ 下非下划线开头的单层目录')
    title = (artifacts / '标题.txt').read_text(encoding='utf-8').strip()
    caption = (artifacts / '配文.txt').read_text(encoding='utf-8').strip()
    cards = sorted((p for p in artifacts.glob('card_*.png') if re.fullmatch(r'card_\d+\.png', p.name)),
                   key=lambda p: int(p.stem.split('_')[1]))
    if (artifacts / 'cover.png').is_file():
        cards.insert(0, artifacts / 'cover.png')
    if not title or not caption or not cards:
        raise ValueError('交付需要标题、配文和最终图片')
    paragraphs = ''.join(f'<p>{escape(p).replace(chr(10), "<br>")}</p>' for p in caption.split('\n\n'))
    figures = ''.join(f'<figure><a href="{escape(p.name)}"><img src="{escape(p.name)}" alt="第 {i} 张图片"></a></figure>' for i, p in enumerate(cards, 1))
    preview = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<style>body{{margin:0;background:#F3F1E9;color:#2F2D29;font:17px/1.75 "Microsoft YaHei",sans-serif}}header,main{{max-width:850px;margin:auto;padding:24px}}h1{{font-size:27px;line-height:1.5;margin:0 0 16px}}p{{margin:0 0 16px}}a{{color:#3568B0}}nav{{display:flex;gap:20px;margin-top:20px}}main{{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding-top:0}}figure{{margin:0}}img{{display:block;width:100%}}@media(max-width:620px){{main{{grid-template-columns:1fr;padding:0;gap:14px}}header{{padding:20px}}}}</style>
<header><h1>{escape(title)}</h1>{paragraphs}<nav><a href="标题.txt">标题</a><a href="配文.txt">配文</a></nav></header><main>{figures}</main></html>'''
    (artifacts / '预览.html').write_text(preview, encoding='utf-8')
    if destination.exists():
        backup = run / 'previous-deliveries' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.parent.mkdir(parents=True, exist_ok=True)
        # Both resolved move targets are inside the intended output/work directories.
        if not backup.resolve().is_relative_to(run):
            raise ValueError('历史交付路径必须位于本次工作目录内')
        destination.rename(backup)
    shutil.copytree(artifacts, destination)
    manifest['published_at'] = datetime.now().astimezone().isoformat()
    manifest['publication_title'] = title
    manifest['published_images'] = [str(destination / p.name) for p in cards]
    manifest['published_title'] = str(destination / '标题.txt')
    manifest['published_caption'] = str(destination / '配文.txt')
    manifest['preview'] = str(destination / '预览.html')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    delivery = run / 'delivery.md'
    image_description = '`cover.png`（封面）、`card_N.png`（主体）' if (artifacts / 'cover.png').is_file() else '`card_N.png`'
    note = f'# 当前交付入口\n\n- 成品目录：{destination}\n- 标题：`标题.txt`\n- 配文：`配文.txt`\n- 图片：{image_description}\n- 预览：`预览.html`\n\n'
    existing = delivery.read_text(encoding='utf-8') if delivery.exists() else ''
    if existing.startswith('# 当前交付入口\n'):
        existing = existing.split('\n\n', 2)[-1]
    delivery.write_text(note + existing, encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', help='本次工作目录（包含 run.json）')
    args = parser.parse_args()
    try:
        result = publish_blog(args.run_dir)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'整理失败：{exc}\n')
    print(json.dumps({'delivery_dir': result['delivery_dir'], 'title': result['published_title'],
                      'caption': result['published_caption'], 'preview': result['preview']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

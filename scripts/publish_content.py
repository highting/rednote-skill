"""在完成状态及真实渲染 QA 通过后发布统一内容，备份并整体替换旧交付。"""

import argparse
from datetime import datetime
import hashlib
from html import escape
import json
from pathlib import Path, PureWindowsPath
import re
import shutil
import struct
import tempfile
from urllib.parse import quote

try:
    from .prepare_content import (PROJECT_ROOT, MODES, SCENES, _assert_name_available,
                                  _hash_tree, _safe_output, _source_identity,
                                  _validate_name, _validate_tree, _write_json)
except ImportError:
    from prepare_content import (PROJECT_ROOT, MODES, SCENES, _assert_name_available,
                                 _hash_tree, _safe_output, _source_identity,
                                 _validate_name, _validate_tree, _write_json)


def _recorded_path(value: str, root: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError('工作记录缺少有效的路径字段')
    candidate = Path(value)
    return (candidate if candidate.is_absolute() else root / candidate).resolve()


def _read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'缺少实际 JSON 记录：{path.name}')
    record = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(record, dict):
        raise ValueError(f'{path.name} 必须是 JSON 对象')
    return record


def _image_path(value, artifacts: Path) -> Path:
    if isinstance(value, dict):
        value = value.get('file', value.get('path'))
    if not isinstance(value, str) or not value:
        raise ValueError('qa.images 每项必须有相对文件名 file')
    relative = Path(value)
    if (relative.is_absolute() or PureWindowsPath(value).drive or '..' in relative.parts
            or '..' in PureWindowsPath(value).parts or '\\' in value):
        raise ValueError('qa.images 不能包含绝对路径或路径逃逸')
    image = artifacts / relative
    if (not image.resolve().is_relative_to(artifacts) or image.is_symlink()
            or not image.is_file() or image.suffix.lower() != '.png'):
        raise ValueError('qa.images 必须引用交付目录内的实际 PNG 文件')
    header = image.read_bytes()[:33]
    if (len(header) < 33 or header[:8] != b'\x89PNG\r\n\x1a\n'
            or header[12:16] != b'IHDR' or not all(struct.unpack('>II', header[16:24]))):
        raise ValueError(f'图片不是有效的有尺寸 PNG：{relative.as_posix()}')
    return image


def _verify_delivery(artifacts: Path, scene: str) -> tuple[dict, list[Path], str | None, str | None]:
    _validate_tree(artifacts)
    main = artifacts / 'index.html'
    if not main.is_file() or not main.read_bytes().strip():
        raise ValueError('交付缺少主 HTML：index.html')
    qa = _read_json(artifacts / 'qa.json')
    if type(qa.get('schema_version')) is not int or qa['schema_version'] != 1:
        raise ValueError('qa.json 必须使用 schema_version=1')
    if qa.get('scene') != scene:
        raise ValueError('qa.json 场景与本次 scene 不一致')
    if qa.get('passed') is not True:
        raise ValueError('实际 qa.json 的 passed 必须为 true')
    recorded_hash = qa.get('html_sha256')
    if (not isinstance(recorded_hash, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', recorded_hash)
            or recorded_hash.lower() != hashlib.sha256(main.read_bytes()).hexdigest()):
        raise ValueError('主 HTML 已变更或 QA 缺少准确的 html_sha256，请重新渲染检查')
    if not isinstance(qa.get('images'), list):
        raise ValueError('qa.json 必须提供有序 images 数组')
    images = [_image_path(value, artifacts) for value in qa['images']]
    if len(set(images)) != len(images):
        raise ValueError('qa.images 不能重复引用同一图片')
    title_path, caption_path = artifacts / '标题.txt', artifacts / '配文.txt'
    title = title_path.read_text(encoding='utf-8').strip() if title_path.is_file() else None
    caption = caption_path.read_text(encoding='utf-8').strip() if caption_path.is_file() else None
    if scene == 'rednote':
        if not images or not title or not caption:
            raise ValueError('rednote 交付需要最终 PNG、非空标题.txt 和配文.txt')
        if any(not re.fullmatch(r'(?:card_\d+|page[-_]\d+|cover)\.png', image.name) for image in images):
            raise ValueError('rednote 只接受正文 page-NN.png、card_N.png 或 cover.png，不能把 preview.png 当成品')
    recorded_files = {image.relative_to(artifacts).as_posix() for image in images}
    stale = [item.name for item in artifacts.iterdir()
             if item.is_file() and re.fullmatch(r'(?:page[-_]\d+|card_\d+|cover|preview)\.png', item.name)
             and item.name not in recorded_files]
    if stale:
        raise ValueError(f'发现未被本次 qa.images 引用的旧输出图片，请重新渲染或清理：{", ".join(sorted(stale))}')
    return qa, images, title, caption


def _write_preview(stage: Path, scene: str, images: list[Path], title: str | None,
                   caption: str | None, topic: str) -> None:
    if scene != 'rednote':
        # An identical copy retains embedded resources and relative local assets.
        shutil.copyfile(stage / 'index.html', stage / '预览.html')
        return
    figures = ''.join(f'<figure><img src="{escape(quote(image.relative_to(stage).as_posix(), safe="/"))}" alt="Page {i}"><figcaption>Page {i}</figcaption></figure>'
                      for i, image in enumerate(images, 1))
    preview = f'''<!doctype html><html lang="en"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Content preview</title>
<style>body{{margin:0;background:#F7F8F5;color:#283331;font:18px/1.8 system-ui,sans-serif}}header,main{{max-width:1000px;margin:auto;padding:28px}}h1{{font-size:30px;line-height:1.5;margin:0 0 18px}}a{{color:#285F62}}nav{{display:flex;gap:22px;margin-top:20px}}main{{display:grid;grid-template-columns:1fr 1fr;gap:24px;padding-top:0}}figure{{margin:0}}figcaption{{font-size:14px;padding-top:8px}}img{{display:block;width:100%}}@media(max-width:650px){{main{{grid-template-columns:1fr;padding:0;gap:16px}}header{{padding:22px}}}}</style>
<header><h1>Content preview</h1><nav><a href="index.html">HTML</a><a href="{quote('标题.txt')}">Title</a><a href="{quote('配文.txt')}">Caption</a></nav></header><main>{figures}</main></html>'''
    (stage / '预览.html').write_text(preview, encoding='utf-8')


def publish_content(run_dir: str, project_root: Path = PROJECT_ROOT) -> dict:
    root = project_root.resolve()
    output = _safe_output(root)
    requested = Path(run_dir)
    run = (requested if requested.is_absolute() else root / requested).resolve()
    relative = run.relative_to(output) if run.is_relative_to(output) else Path('.')
    if (len(relative.parts) != 3 or relative.parts[0] != '_work'
            or not run.is_dir() or requested.is_symlink()):
        raise ValueError('工作目录必须是 output/_work/<短名>/<本次目录>')
    name = _validate_name(relative.parts[1])
    manifest_path = run / 'run.json'
    manifest = _read_json(manifest_path)
    if manifest.get('status') != 'completed':
        raise ValueError('实际内容与渲染检查完成并标记 completed 后才能交付')
    scene, mode = manifest.get('scene'), manifest.get('mode')
    if scene not in SCENES or mode not in MODES:
        raise ValueError('工作记录缺少有效的 scene/mode')
    identity = _source_identity(manifest, root)
    for key, expected in {'run_dir': run, 'source_dir': run / 'source', 'work_dir': run / 'work',
                          'artifact_dir': run / 'delivery', 'delivery_dir': output / name}.items():
        if _recorded_path(manifest.get(key), root) != expected:
            raise ValueError(f'{key} 与工作目录约定不一致，禁止路径逃逸或覆盖原稿')
    source, work, artifacts, destination = run / 'source', run / 'work', run / 'delivery', output / name
    for key, expected in {'main_html': artifacts / 'index.html', 'qa_file': artifacts / 'qa.json',
                          'title_file': artifacts / '标题.txt', 'caption_file': artifacts / '配文.txt'}.items():
        if key in manifest and _recorded_path(manifest[key], root) != expected:
            raise ValueError(f'{key} 与成品位置不一致')
    if manifest.get('work_entry') and not _recorded_path(manifest['work_entry'], root).is_relative_to(work):
        raise ValueError('work_entry 必须留在本次 work/ 中')
    if not isinstance(manifest.get('source_sha256'), dict) or _hash_tree(source) != manifest['source_sha256']:
        raise ValueError('不可变 source 快照已变化或缺少哈希记录')
    _assert_name_available(root, name, identity)
    qa, images, title, caption = _verify_delivery(artifacts, scene)
    image_names = [image.relative_to(artifacts).as_posix() for image in images]
    published_at = datetime.now().astimezone().isoformat()
    stage = Path(tempfile.mkdtemp(prefix='publish-', dir=run))
    backup = None
    try:
        shutil.copytree(artifacts, stage, dirs_exist_ok=True, symlinks=True)
        _, staged_images, _, _ = _verify_delivery(stage, scene)
        _write_preview(stage, scene, staged_images, title, caption, manifest.get('topic', name))
        _write_json(stage / 'delivery.json', {'schema_version': 1, 'input_id': identity,
                    'topic': manifest.get('topic', name), 'entry': manifest.get('entry'),
                    'scene': scene, 'mode': mode, 'scope': manifest.get('scope'),
                    'published_at': published_at, 'main_html': 'index.html',
                    'html_sha256': qa['html_sha256'], 'images': image_names, 'qa': 'qa.json'})
        if destination.exists():
            _validate_tree(destination)
            backup = run / 'previous-deliveries' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            if backup.parent.is_symlink() or not backup.resolve().is_relative_to(run):
                raise ValueError('备份路径不能逃逸出本次工作目录')
            backup.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(backup)
        try:
            stage.rename(destination)
        except OSError:
            if backup is not None and not destination.exists():
                backup.rename(destination)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    manifest.update({'published_at': published_at, 'publication_status': 'published',
                     'publication_title': title or manifest.get('topic', name),
                     'published_images': [str(destination / name) for name in image_names],
                     'published_html': str(destination / 'index.html'),
                     'published_qa': str(destination / 'qa.json'),
                     'published_title': str(destination / '标题.txt') if title else None,
                     'published_caption': str(destination / '配文.txt') if caption else None,
                     'preview': str(destination / '预览.html'),
                     'previous_delivery': str(backup) if backup is not None else None})
    _write_json(manifest_path, manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', help='output/_work/<短名>/<本次目录>（包含 run.json）')
    args = parser.parse_args()
    try:
        result = publish_content(args.run_dir)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f'交付失败：{exc}\n')
    print(json.dumps({key: result[key] for key in ('delivery_dir', 'published_html', 'preview',
                     'published_title', 'published_caption', 'published_images')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

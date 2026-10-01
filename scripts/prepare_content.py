"""准备统一内容工作区和任务 Prompt，保留原稿快照；不调用生成模型。"""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import stat


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENES = ('learning', 'blog', 'report', 'rednote', 'diagram')
MODES = ('html', 'images')
DOCUMENT_SUFFIXES = {'.md', '.markdown', '.txt', '.docx', '.pdf', '.html', '.htm', '.rst'}
DEFAULT_SCOPES = {
    'learning': '完整学习文 HTML：必要前置、推导、贯穿算例、机制图和边界。',
    'blog': '完整技术博客 HTML：中心问题、论证、例证、机制图和实现边界。',
    'report': '技术汇报 HTML 幻灯片：适配有限讲述时间，页内结论与证据、讲者备注和必要限制。',
    'rednote': '连续正文图文：HTML 分页 PNG、必要辅助图、发布标题和摘要配文。',
    'diagram': '仅制作指定解释图，注明关系与插入位置，不扩写整篇正文。',
}


def _write_json(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + '.tmp')
    if temporary.is_symlink():
        raise ValueError('JSON 临时文件不能是符号链接')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def _validate_name(name: str) -> str:
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{prefix}{i}' for prefix in ('COM', 'LPT') for i in range(1, 10)}
    if (not isinstance(name, str) or not name or name != name.strip()
            or name in ('.', '..') or name.startswith('_') or name.endswith('.')
            or any(character in name for character in '/\\:\0')
            or any(ord(character) < 32 for character in name)
            or PureWindowsPath(name).drive or name.split('.')[0].upper() in reserved):
        raise ValueError('--name 必须是安全的单层短名，不能以下划线开头或含路径分隔符')
    return name


def _safe_output(root: Path) -> Path:
    output = root / 'output'
    if output.is_symlink() or output.resolve() != output or (output.exists() and not output.is_dir()):
        raise ValueError('output 必须是项目内的实际目录，不能使用符号链接')
    work = output / '_work'
    if work.is_symlink() or work.resolve() != work or (work.exists() and not work.is_dir()):
        raise ValueError('output/_work 必须是项目内的实际目录')
    return output


def _validate_tree(directory: Path) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('材料或成品必须是实际目录')
    for item in directory.rglob('*'):
        if item.is_symlink() or not item.resolve().is_relative_to(directory):
            raise ValueError(f'材料或成品不能包含符号链接／路径逃逸：{item}')
        if not item.is_file() and not item.is_dir():
            raise ValueError(f'材料或成品包含不支持的文件类型：{item}')


def _hash_tree(directory: Path) -> dict:
    _validate_tree(directory)
    return {
        item.relative_to(directory).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(directory.rglob('*')) if item.is_file()
    }


def _source_identity(manifest: dict, root: Path) -> str:
    if not isinstance(manifest, dict):
        raise ValueError('工作记录必须是 JSON 对象')
    recorded = manifest.get('input_id')
    input_dir = manifest.get('input_dir')
    if input_dir is not None and (not isinstance(input_dir, str) or not input_dir):
        raise ValueError('工作记录中的 input_dir 不合法')
    def input_path() -> Path:
        candidate = Path(input_dir)
        return (candidate if candidate.is_absolute() else root / candidate).resolve()
    if recorded:
        if not isinstance(recorded, str) or '\\' in recorded or PureWindowsPath(recorded).drive:
            raise ValueError('工作记录中的 input_id 不合法')
        relative = Path(recorded)
        if (relative.is_absolute() or '..' in relative.parts or len(relative.parts) < 3
                or relative.parts[0] not in ('inputs', 'blogs')):
            raise ValueError('工作记录中的 input_id 不合法')
        identity = relative.as_posix()
        if input_dir and input_path() != root / relative:
            raise ValueError('工作记录中的输入字段不一致')
        return identity
    if not input_dir:
        raise ValueError('工作记录缺少输入目录，无法确认短名归属')
    source = input_path()
    if not source.is_relative_to(root):
        raise ValueError('工作记录中的输入目录不属于本项目')
    relative = source.relative_to(root)
    if len(relative.parts) < 3 or relative.parts[0] not in ('inputs', 'blogs'):
        raise ValueError('工作记录中的输入目录不合法')
    return relative.as_posix()


def _assert_name_available(root: Path, name: str, identity: str) -> None:
    output = _safe_output(root)
    destination, runs = output / name, output / '_work' / name
    for candidate in (destination, runs):
        if candidate.is_symlink() or candidate.resolve() != candidate:
            raise ValueError('交付或工作路径不能是符号链接')
        if candidate.exists() and not candidate.is_dir():
            raise ValueError('交付或工作路径必须为目录')
    legacy_published = False
    if runs.exists():
        for old_run in runs.iterdir():
            if old_run.is_symlink():
                raise ValueError('历史工作目录不能是符号链接')
            record = old_run / 'run.json'
            if not record.is_file():
                continue
            if record.is_symlink():
                raise ValueError('历史工作记录不能是符号链接')
            previous = json.loads(record.read_text(encoding='utf-8'))
            if _source_identity(previous, root) != identity:
                raise ValueError('短名冲突：不同主题不能共用同一个 output/<短名>')
            if previous.get('workflow') != 'content' and previous.get('published_at'):
                legacy_published = True
    if destination.exists():
        ownership = destination / 'delivery.json'
        if ownership.is_symlink():
            raise ValueError('交付归属记录不能是符号链接')
        if ownership.is_file():
            recorded = json.loads(ownership.read_text(encoding='utf-8'))
            if not isinstance(recorded, dict):
                raise ValueError('交付归属记录必须是 JSON 对象')
            if recorded.get('input_id') != identity:
                raise ValueError('短名冲突：现有交付属于其他输入主题')
        elif not legacy_published:
            raise ValueError('无法确认现有交付的短名归属，请使用另一个 --name')


def select_entry(materials: Path, entry: str | None = None) -> Path:
    if entry:
        relative = Path(entry)
        if relative.is_absolute() or PureWindowsPath(entry).drive or '..' in relative.parts:
            raise ValueError('--entry 必须是素材目录内的相对文件路径')
        selected = (materials / relative).resolve()
        if not selected.is_relative_to(materials) or not selected.is_file():
            raise ValueError('--entry 必须指向素材目录内的实际文件')
        return selected
    for name in ('main.md', 'article.md', 'index.md', 'main.txt', 'article.txt'):
        if (materials / name).is_file():
            return materials / name
    candidates = sorted(item for item in materials.rglob('*')
                        if item.is_file() and item.suffix.lower() in DOCUMENT_SUFFIXES)
    if len(candidates) != 1:
        names = ', '.join(item.relative_to(materials).as_posix() for item in candidates)
        raise ValueError(f'无法确定唯一正文，请用 --entry 指定。候选：{names or "无"}')
    return candidates[0]


def prepare_content(content_path: str, scene: str = 'learning', mode: str = 'html',
                    entry: str | None = None, project_root: Path = PROJECT_ROOT,
                    output_name: str | None = None, scope: str | None = None,
                    topic: str | None = None) -> dict:
    root = project_root.resolve()
    if scene not in SCENES or mode not in MODES:
        raise ValueError('scene 或 mode 不支持；mode 仅决定辅助图制作工具')
    materials = (root / content_path).resolve()
    if not materials.is_dir() or not materials.is_relative_to(root):
        raise ValueError('素材必须是本项目 inputs/ 或 blogs/ 内的现有目录')
    relative = materials.relative_to(root)
    if len(relative.parts) < 3 or relative.parts[0] not in ('inputs', 'blogs'):
        raise ValueError('输入路径应为 inputs/<分类>/<主题> 或 blogs/<分类>/<主题>')
    if (root / relative.parts[0]).is_symlink():
        raise ValueError('输入根目录不能是符号链接')
    _validate_tree(materials)
    selected = select_entry(materials, entry).relative_to(materials)
    if (materials / '任务Prompt.txt').exists():
        raise ValueError('素材中的任务Prompt.txt 与工作区生成文件同名，请先更名')
    name = _validate_name(relative.name if output_name is None else output_name)
    identity = relative.as_posix()
    _assert_name_available(root, name, identity)
    common_file, scene_file = root / 'prompts/common.txt', root / f'prompts/scenes/{scene}.txt'
    for prompt in (common_file, scene_file):
        if prompt.is_symlink() or not prompt.is_file() or not prompt.resolve().is_relative_to(root):
            raise ValueError(f'缺少项目内的 Prompt 文件：{prompt.relative_to(root)}')
    common, scene_prompt = common_file.read_text(encoding='utf-8'), scene_file.read_text(encoding='utf-8')
    if not common.strip() or not scene_prompt.strip():
        raise ValueError('通用和场景 Prompt 必须包含内容')
    title = relative.name if topic is None else topic.strip()
    contract = DEFAULT_SCOPES[scene] if scope is None else scope.strip()
    if not title or not contract:
        raise ValueError('主题和约定范围不能为空')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output = _safe_output(root)
    run = output / '_work' / name / f'{stamp}-{scene}-{mode}'
    run.mkdir(parents=True, exist_ok=False)
    manifest = {
        'schema_version': 1, 'workflow': 'content', 'input_id': identity,
        'input_kind': relative.parts[0], 'input_dir': str(materials),
        'blog': Path(*relative.parts[1:]).as_posix(),
        'topic': title, 'entry': selected.as_posix(), 'scene': scene, 'mode': mode,
        'scope': contract, 'created_at': datetime.now().astimezone().isoformat(),
        'status': 'preparing', 'run_dir': str(run), 'source_dir': str(run / 'source'),
        'work_dir': str(run / 'work'), 'work_entry': str(run / 'work' / selected),
        'artifact_dir': str(run / 'delivery'), 'delivery_dir': str(output / name),
        'prompt_file': str(run / 'work' / '任务Prompt.txt'),
        'prompt_sources': ['prompts/common.txt', f'prompts/scenes/{scene}.txt'],
        'main_html': str(run / 'delivery' / 'index.html'),
        'generated_html': str(run / 'work' / 'index.html'),
        'qa_file': str(run / 'delivery' / 'qa.json'),
        'title_file': str(run / 'delivery' / '标题.txt'),
        'caption_file': str(run / 'delivery' / '配文.txt'),
        'renderer_command': ['python', 'scripts/render_content.py', str(run / 'work' / 'index.html'), '--scene', scene,
                             '--output-dir', str(run / 'delivery')],
    }
    if scene == 'report':
        manifest['renderer_command'].extend(['--activate-hook', 'activateContentExport'])
    try:
        shutil.copytree(materials, run / 'source')
        shutil.copytree(run / 'source', run / 'work')
        for item in [run / 'work', *(run / 'work').rglob('*')]:
            item.chmod(item.stat().st_mode | stat.S_IWUSR)
        (run / 'delivery').mkdir()
        manifest['source_sha256'] = _hash_tree(run / 'source')
        for item in (run / 'source').rglob('*'):
            item.chmod(item.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        (run / 'source').chmod((run / 'source').stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        mode_description = 'HTML＋SVG（仅辅助图）' if mode == 'html' else 'ImageGen（仅辅助图，正文仍用 HTML）'
        context = (f'【本次任务】\n主题：{title}\n场景：{scene}\n辅助图制作工具：{mode_description}\n'
                   f'约定范围：{contract}\n原始素材：{identity}\n入口（保持相对路径）：{selected.as_posix()}\n'
                   f'工作稿：{manifest["work_entry"]}\n任务交付目录：{manifest["artifact_dir"]}\n'
                   '先阅读实际素材，再完成生成与真实渲染检查。source/ 是不可修改快照；在 work/ 修改稿件。\n'
                   f'生成 HTML 入口：{manifest["generated_html"]}\n'
                   '生成上述 HTML 后运行 renderer_command；qa.json 通过后再标记 completed 并发布。\n')
        Path(manifest['prompt_file']).write_text(context + '\n' + common.rstrip() + '\n\n' + scene_prompt.rstrip() + '\n', encoding='utf-8')
        (run / 'delivery.md').write_text(f'# {title}\n\n状态：prepared，尚未生成。\n\n场景：{scene}\n约定范围：{contract}\n\n记录来源、图解选点、内容完整性与实际视觉检查后再交付。\n', encoding='utf-8')
        manifest['status'] = 'prepared'
    except (OSError, ValueError) as exc:
        manifest['status'], manifest['error'] = 'failed', str(exc)
        raise
    finally:
        _write_json(run / 'run.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('content', help='inputs/<分类>/<主题>；也兼容 blogs/<分类>/<主题>')
    parser.add_argument('--scene', choices=SCENES, default='learning')
    parser.add_argument('--mode', choices=MODES, default='html', help='仅选择辅助图工具：html 为 HTML＋SVG，images 为 ImageGen')
    parser.add_argument('--entry', help='相对于素材文件夹的正文入口')
    parser.add_argument('--name', help='output/ 下的单层短名')
    parser.add_argument('--topic', help='明确主题；默认素材文件夹名')
    parser.add_argument('--scope', help='本次约定范围；默认按场景生成完整内容')
    args = parser.parse_args()
    try:
        result = prepare_content(args.content, args.scene, args.mode, args.entry,
                                 output_name=args.name, scope=args.scope, topic=args.topic)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'准备失败：{exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

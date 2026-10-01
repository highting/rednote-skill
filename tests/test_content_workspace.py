"""Real filesystem lifecycle tests; renderer QA fixtures do not replace browser tests."""

import base64
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts.prepare_blog import prepare_blog
from scripts.publish_blog import publish_blog
from scripts.prepare_content import prepare_content
from scripts.publish_content import publish_content


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5k0AAAAASUVORK5CYII=')
SCENES = ('learning', 'blog', 'report', 'rednote')


class ContentWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.addCleanup(self.make_writable)
        self.materials = self.root / 'inputs' / '机器学习' / '中文 主题'
        self.materials.mkdir(parents=True)
        (self.materials / 'main.md').write_text('原稿。![图](images/图.svg)', encoding='utf-8')
        (self.materials / 'images').mkdir()
        (self.materials / 'images' / '图.svg').write_text('<svg/>', encoding='utf-8')
        (self.root / 'prompts/scenes').mkdir(parents=True)
        (self.root / 'prompts/common.txt').write_text('COMMON-PROMPT：通用规则', encoding='utf-8')
        for scene in (*SCENES, 'diagram'):
            (self.root / f'prompts/scenes/{scene}.txt').write_text(f'SCENE-PROMPT-{scene}', encoding='utf-8')

    def make_writable(self):
        for item in [self.root, *self.root.rglob('*')]:
            if item.exists() and not item.is_symlink():
                item.chmod(item.stat().st_mode | stat.S_IWUSR)

    def prepare(self, **kwargs):
        return prepare_content(str(self.materials), project_root=self.root, **kwargs)

    def save(self, manifest):
        (Path(manifest['run_dir']) / 'run.json').write_text(json.dumps(manifest), encoding='utf-8')

    def ready(self, manifest, images=None):
        artifacts = Path(manifest['artifact_dir'])
        (artifacts / 'index.html').write_text('<!doctype html><html><body>Complete output</body></html>', encoding='utf-8')
        image_names = images if images is not None else (['page-01.png'] if manifest['scene'] in ('rednote', 'report') else ['preview.png'])
        for name in image_names:
            image = artifacts / name
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(PNG)
        qa = {'schema_version': 1, 'scene': manifest['scene'], 'passed': True,
              'html_sha256': hashlib.sha256((artifacts / 'index.html').read_bytes()).hexdigest(),
              'images': [{'file': name} for name in image_names]}
        (artifacts / 'qa.json').write_text(json.dumps(qa), encoding='utf-8')
        if manifest['scene'] == 'rednote':
            (artifacts / '标题.txt').write_text('直接说明技术主题', encoding='utf-8')
            (artifacts / '配文.txt').write_text('我把这次阅读的关键过程整理成图。', encoding='utf-8')
        manifest['status'] = 'completed'
        self.save(manifest)
        return qa

    def write_qa(self, manifest, qa):
        (Path(manifest['artifact_dir']) / 'qa.json').write_text(json.dumps(qa), encoding='utf-8')

    def test_four_scenes_prepare_snapshots_prompts_and_renderer_contract(self):
        original = (self.materials / 'main.md').read_bytes()
        for scene in SCENES:
            with self.subTest(scene=scene):
                result = self.prepare(scene=scene, mode='images', output_name=scene)
                run = Path(result['run_dir'])
                self.assertTrue(run.name.endswith(f'-{scene}-images'))
                self.assertEqual(run.parent, self.root / 'output/_work' / scene)
                self.assertEqual(result['status'], 'prepared')
                self.assertEqual(result['entry'], 'main.md')
                self.assertEqual(result['input_id'], 'inputs/机器学习/中文 主题')
                self.assertEqual(result['blog'], '机器学习/中文 主题')
                self.assertEqual(list(Path(result['artifact_dir']).iterdir()), [])
                prompt = Path(result['prompt_file']).read_text(encoding='utf-8')
                self.assertIn('COMMON-PROMPT', prompt)
                self.assertIn(f'SCENE-PROMPT-{scene}', prompt)
                self.assertIn(result['scope'], prompt)
                self.assertIn('仅辅助图，正文仍用 HTML', prompt)
                self.assertEqual(result['renderer_command'][2], result['generated_html'])
                if scene == 'report':
                    self.assertIn('讲者备注', result['scope'])
                    self.assertEqual(result['renderer_command'][-2:], ['--activate-hook', 'activateContentExport'])
                Path(result['work_entry']).write_text('工作稿修改', encoding='utf-8')
                self.assertEqual((run / 'source/main.md').read_bytes(), original)
                self.assertEqual((self.materials / 'main.md').read_bytes(), original)
                self.assertEqual((run / 'work/images/图.svg').read_text(), '<svg/>')
                self.assertFalse((run / 'source/main.md').stat().st_mode & stat.S_IWUSR)
                self.assertTrue(Path(result['work_entry']).stat().st_mode & stat.S_IWUSR)
                self.assertEqual(json.loads((run / 'run.json').read_text(encoding='utf-8')), result)

    def test_four_scenes_publish_valid_qa_without_forcing_captions_elsewhere(self):
        for scene in SCENES:
            with self.subTest(scene=scene):
                result = self.prepare(scene=scene, output_name=scene)
                self.ready(result)
                published = publish_content(result['run_dir'], project_root=self.root)
                final = Path(published['delivery_dir'])
                self.assertTrue((final / 'index.html').is_file())
                self.assertTrue((final / 'qa.json').is_file())
                self.assertTrue((final / '预览.html').is_file())
                ownership = json.loads((final / 'delivery.json').read_text(encoding='utf-8'))
                self.assertEqual(ownership['scene'], scene)
                self.assertEqual(ownership['input_id'], result['input_id'])
                if scene == 'rednote':
                    self.assertEqual(Path(published['published_caption']).parent, final)
                    self.assertIn('page-01.png', (final / '预览.html').read_text(encoding='utf-8'))
                else:
                    self.assertIsNone(published['published_caption'])
                    self.assertIsNone(published['published_title'])
                    self.assertFalse((final / '配文.txt').exists())
                    self.assertEqual((final / '预览.html').read_bytes(), (final / 'index.html').read_bytes())

    def test_new_runs_and_publish_replace_whole_delivery_with_backup(self):
        first = self.prepare(scene='rednote', output_name='Test')
        self.ready(first, ['page-01.png', 'page-02.png'])
        final = Path(publish_content(first['run_dir'], project_root=self.root)['delivery_dir'])
        (final / '用户备注.txt').write_text('必须保留', encoding='utf-8')
        second = self.prepare(scene='rednote', output_name='Test')
        self.assertNotEqual(first['run_dir'], second['run_dir'])
        self.ready(second, ['page-01.png'])
        published = publish_content(second['run_dir'], project_root=self.root)
        self.assertFalse((final / 'page-02.png').exists())
        self.assertFalse((final / '用户备注.txt').exists())
        backup = Path(published['previous_delivery'])
        self.assertEqual((backup / '用户备注.txt').read_text(encoding='utf-8'), '必须保留')
        self.assertEqual((backup / 'page-02.png').read_bytes(), PNG)
        self.assertTrue((Path(first['artifact_dir']) / 'page-02.png').is_file())

    def test_legacy_blogs_and_legacy_published_ownership_remain_compatible(self):
        blog = self.root / 'blogs/论文阅读/旧博客'
        blog.mkdir(parents=True)
        (blog / 'main.md').write_text('旧博客原稿', encoding='utf-8')
        old = prepare_blog(str(blog), project_root=self.root, output_name='Legacy')
        old_artifacts = Path(old['artifact_dir'])
        (old_artifacts / '标题.txt').write_text('旧标题', encoding='utf-8')
        (old_artifacts / '配文.txt').write_text('旧配文', encoding='utf-8')
        (old_artifacts / 'card_1.png').write_bytes(PNG)
        old['status'] = 'completed'
        self.save(old)
        publish_blog(old['run_dir'], project_root=self.root)
        result = prepare_content(str(blog), scene='blog', project_root=self.root, output_name='Legacy')
        self.assertEqual(result['input_kind'], 'blogs')
        self.assertEqual(result['blog'], '论文阅读/旧博客')
        self.ready(result)
        published = publish_content(result['run_dir'], project_root=self.root)
        self.assertEqual((blog / 'main.md').read_text(encoding='utf-8'), '旧博客原稿')
        self.assertTrue((Path(published['previous_delivery']) / 'card_1.png').is_file())

    def test_nested_entry_preserves_relative_assets_and_pdf_is_not_converted(self):
        (self.materials / '正文').mkdir()
        (self.materials / '正文/paper.pdf').write_bytes(b'PDF source, not converted')
        result = self.prepare(entry='正文/paper.pdf')
        self.assertEqual(result['entry'], '正文/paper.pdf')
        self.assertTrue((Path(result['work_entry']).parent / '../images/图.svg').is_file())
        self.assertFalse(Path(result['main_html']).exists())

    def test_ambiguous_entry_and_missing_prompt_fail_before_output(self):
        (self.materials / 'main.md').rename(self.materials / '初稿.md')
        (self.materials / '修订.md').write_text('第二稿', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '唯一正文'):
            self.prepare()
        self.assertFalse((self.root / 'output').exists())
        (self.root / 'prompts/common.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'Prompt'):
            self.prepare(entry='修订.md')
        self.assertFalse((self.root / 'output').exists())

    def test_input_entry_name_and_symlink_escapes_are_rejected(self):
        for name in ('../outside', '/outside', 'nested/name', r'nested\name', '_work', '.', '..', 'C:drive', 'CON', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.prepare(output_name=name)
        for entry in ('../outside.md', str(self.materials / 'main.md'), r'C:\outside.md'):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                self.prepare(entry=entry)
        for input_path in (self.root, self.root / 'inputs/机器学习'):
            with self.assertRaises(ValueError):
                prepare_content(str(input_path), project_root=self.root)
        (self.materials / 'escape.md').symlink_to(self.root / 'prompts/common.txt')
        with self.assertRaisesRegex(ValueError, '符号链接'):
            self.prepare()
        self.assertFalse((self.root / 'output').exists())

    def test_short_name_conflicts_and_unknown_existing_directory_are_rejected(self):
        self.prepare(output_name='Reserved')
        other = self.root / 'inputs/工程实践/别的主题'
        other.mkdir(parents=True)
        (other / 'main.md').write_text('另一篇', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '短名冲突'):
            prepare_content(str(other), project_root=self.root, output_name='Reserved')
        unknown = self.root / 'output/Unknown'
        unknown.mkdir()
        (unknown / 'keep.txt').write_text('不得覆盖')
        with self.assertRaisesRegex(ValueError, '归属'):
            self.prepare(output_name='Unknown')
        self.assertEqual((unknown / 'keep.txt').read_text(), '不得覆盖')

    def test_publish_requires_completed_actual_qa_and_main_html(self):
        result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'completed'):
            publish_content(result['run_dir'], project_root=self.root)
        result['status'] = 'completed'
        self.save(result)
        with self.assertRaisesRegex(ValueError, 'index.html'):
            publish_content(result['run_dir'], project_root=self.root)
        self.ready(result)
        (Path(result['artifact_dir']) / 'qa.json').unlink()
        with self.assertRaisesRegex(ValueError, 'JSON'):
            publish_content(result['run_dir'], project_root=self.root)
        self.assertFalse(Path(result['delivery_dir']).exists())

    def test_bad_or_stale_qa_is_rejected_without_touching_existing_delivery(self):
        first = self.prepare(output_name='Stable')
        self.ready(first)
        publish_content(first['run_dir'], project_root=self.root)
        final = Path(first['delivery_dir'])
        original = (final / 'index.html').read_bytes()
        result = self.prepare(output_name='Stable')
        qa = self.ready(result)
        for key, value in [('passed', False), ('passed', 'true'), ('scene', 'blog'),
                           ('schema_version', True), ('html_sha256', '0' * 64), ('images', None)]:
            with self.subTest(key=key, value=value):
                self.write_qa(result, {**qa, key: value})
                with self.assertRaises(ValueError):
                    publish_content(result['run_dir'], project_root=self.root)
                self.assertEqual((final / 'index.html').read_bytes(), original)
        for key in ('schema_version', 'scene', 'html_sha256', 'images'):
            missing = dict(qa)
            del missing[key]
            self.write_qa(result, missing)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                publish_content(result['run_dir'], project_root=self.root)
        self.write_qa(result, qa)
        (Path(result['artifact_dir']) / 'index.html').write_text('<html>changed after QA</html>')
        with self.assertRaisesRegex(ValueError, 'HTML 已变更'):
            publish_content(result['run_dir'], project_root=self.root)

    def test_publish_rejects_manifest_escapes_and_original_overwrite(self):
        result = self.prepare()
        self.ready(result)
        for key, value in [('artifact_dir', result['source_dir']), ('delivery_dir', str(self.materials)),
                           ('source_dir', str(self.materials)), ('work_entry', str(self.materials / 'main.md')),
                           ('main_html', str(self.materials / 'main.md'))]:
            modified = {**result, key: value}
            self.save(modified)
            with self.subTest(key=key), self.assertRaises(ValueError):
                publish_content(result['run_dir'], project_root=self.root)
        self.assertEqual((self.materials / 'main.md').read_text(encoding='utf-8'), '原稿。![图](images/图.svg)')
        with self.assertRaises(ValueError):
            publish_content(str(self.materials), project_root=self.root)

    def test_modified_snapshot_and_artifact_symlinks_cannot_publish(self):
        result = self.prepare()
        self.ready(result)
        snapshot = Path(result['source_dir']) / 'main.md'
        snapshot.chmod(snapshot.stat().st_mode | stat.S_IWUSR)
        snapshot.write_text('changed snapshot')
        with self.assertRaisesRegex(ValueError, '快照'):
            publish_content(result['run_dir'], project_root=self.root)
        fresh = self.prepare(output_name='Fresh')
        self.ready(fresh)
        (Path(fresh['artifact_dir']) / 'external.txt').symlink_to(self.materials / 'main.md')
        with self.assertRaisesRegex(ValueError, '符号链接'):
            publish_content(fresh['run_dir'], project_root=self.root)

    def test_rednote_requires_actual_ordered_png_and_publication_text(self):
        result = self.prepare(scene='rednote')
        qa = self.ready(result, ['page-02.png', 'page-01.png'])
        for filename in ('标题.txt', '配文.txt'):
            file = Path(result['artifact_dir']) / filename
            text = file.read_text(encoding='utf-8')
            file.write_text('')
            with self.assertRaisesRegex(ValueError, 'rednote'):
                publish_content(result['run_dir'], project_root=self.root)
            file.write_text(text, encoding='utf-8')
        bad_names = [[], [{'file': '../page-01.png'}], [{'file': str(self.materials / 'images/图.svg')}],
                     [{'file': 'page-01.png'}, {'file': 'page-01.png'}]]
        for names in bad_names:
            self.write_qa(result, {**qa, 'images': names})
            with self.subTest(images=names), self.assertRaises(ValueError):
                publish_content(result['run_dir'], project_root=self.root)
        artifact = Path(result['artifact_dir'])
        (artifact / 'preview.png').write_bytes(PNG)
        self.write_qa(result, {**qa, 'images': [{'file': 'preview.png'}]})
        with self.assertRaisesRegex(ValueError, 'preview.png'):
            publish_content(result['run_dir'], project_root=self.root)
        (artifact / 'preview.png').unlink()
        self.write_qa(result, qa)
        (artifact / 'page-02.png').write_bytes(b'not PNG')
        with self.assertRaisesRegex(ValueError, 'PNG'):
            publish_content(result['run_dir'], project_root=self.root)
        (artifact / 'page-02.png').write_bytes(PNG)
        published = publish_content(result['run_dir'], project_root=self.root)
        self.assertEqual([Path(name).name for name in published['published_images']], ['page-02.png', 'page-01.png'])
        preview = Path(published['preview']).read_text(encoding='utf-8')
        self.assertLess(preview.index('page-02.png'), preview.index('page-01.png'))

    def test_qa_path_field_compatibility_and_empty_images_for_html_scenes(self):
        result = self.prepare(scene='blog', output_name='Compat')
        qa = self.ready(result)
        qa['images'] = [{'path': 'preview.png'}]
        self.write_qa(result, qa)
        publish_content(result['run_dir'], project_root=self.root)
        fresh = self.prepare(scene='blog', output_name='NoImages')
        self.ready(fresh, [])
        published = publish_content(fresh['run_dir'], project_root=self.root)
        self.assertEqual(published['published_images'], [])

    def test_output_symlink_cannot_point_at_original_materials(self):
        (self.root / 'output').symlink_to(self.materials, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'output'):
            self.prepare()
        self.assertFalse((self.materials / '_work').exists())

    def test_same_run_page_reduction_rejects_stale_pages_but_preserves_other_assets(self):
        result = self.prepare(scene='rednote')
        self.ready(result, ['page-01.png', 'page-02.png'])
        self.ready(result, ['page-01.png'])
        artifacts = Path(result['artifact_dir'])
        (artifacts / 'supporting-diagram.png').write_bytes(PNG)
        with self.assertRaisesRegex(ValueError, '旧输出图片'):
            publish_content(result['run_dir'], project_root=self.root)
        (artifacts / 'page-02.png').unlink()
        published = publish_content(result['run_dir'], project_root=self.root)
        final = Path(published['delivery_dir'])
        self.assertTrue((final / 'supporting-diagram.png').is_file())
        self.assertFalse((final / 'page-02.png').exists())

    def test_failed_replacement_restores_previous_delivery(self):
        first = self.prepare(output_name='Transactional')
        self.ready(first)
        final = Path(publish_content(first['run_dir'], project_root=self.root)['delivery_dir'])
        (final / 'keep.txt').write_text('previous delivery')
        second = self.prepare(output_name='Transactional')
        self.ready(second)
        original_rename = Path.rename
        def fail_stage_move(source, target):
            if source.name.startswith('publish-') and Path(target) == final:
                raise OSError('simulated replacement failure')
            return original_rename(source, target)
        with patch.object(Path, 'rename', fail_stage_move), self.assertRaises(OSError):
            publish_content(second['run_dir'], project_root=self.root)
        self.assertEqual((final / 'keep.txt').read_text(), 'previous delivery')
        self.assertEqual(list(Path(second['run_dir']).glob('publish-*')), [])


if __name__ == '__main__':
    unittest.main()

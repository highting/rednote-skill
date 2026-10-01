"""由公共源和场景规则导出独立可复制 Prompt；不调用生成模型。"""
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENES = ('learning', 'blog', 'report', 'rednote', 'diagram')

def assemble_prompt(scene: str, root: Path = PROJECT_ROOT) -> str:
    if scene not in SCENES:
        raise ValueError(f'未知场景：{scene}')
    shared = (root / 'prompts/common.txt').read_text(encoding='utf-8').strip()
    specific = (root / f'prompts/scenes/{scene}.txt').read_text(encoding='utf-8').strip()
    return shared + '\n\n' + specific + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT_ROOT / 'prompts/standalone')
    parser.add_argument('--scene', choices=SCENES, help='省略时导出全部场景')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for scene in ([args.scene] if args.scene else SCENES):
        target = args.output_dir / f'{scene}.txt'
        target.write_text(assemble_prompt(scene), encoding='utf-8')
        print(target)

if __name__ == '__main__':
    main()

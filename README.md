# RedNote-Render-Skill

将技术材料制作成学习长文、技术博客、技术汇报或小红书图文。先按场景策划，AI制作完整、自包含的离线HTML，再用统一脚本检查或导出PNG。技能名保持 `rednote-render-skill`，兼容旧插件与Markdown分页入口。

| 场景 | 用途 | 默认成品 |
|---|---|---|
| `learning` | 系统学习概念、机制与必要推导 | HTML与桌面检查 |
| `blog` | 独立阅读和分享技术论点 | HTML与桌面检查 |
| `report` | 在有限时间帮助团队形成判断 | 16:9演示HTML、目录/键盘导航/备注、逐页PNG |
| `rednote` | 按图片顺序理解选定主题 | 3:4 PNG、HTML、标题与摘要配文 |
| `diagram` | 明确只要局部解释图或总览图 | 标记的独立图及源文件 |

四个内容场景分别组织，不只是换标题或画幅。`html/images` 仅选择辅助图工具；正文仍可靠排版，精确数值、shape、算法状态与几何用程序图。生图只用于合适且实际可用的辅助视觉。脚本不会自动撰稿、调用生图API或上传社交平台。

## 新流程

将原稿、图片和附件放在 `inputs/<分类>/<主题>/`，保留相对路径；已有 `blogs/` 兼容，不需搬迁。原稿不变，本次制作发生在独立工作副本。

```bash
# 1. 准备材料快照、工作副本、任务Prompt和run.json
python -X utf8 scripts/prepare_content.py "inputs/机器学习/在线Softmax" \
  --scene learning --mode html

# 2. AI读取材料及公共/所选场景Prompt，制作work/index.html
# 3. 检查；learning/blog默认不导出额外长图
python -X utf8 scripts/render_content.py "<run_dir>/work/index.html" \
  --scene learning --output-dir "<run_dir>/delivery"

# 4. 实际查看成品并记录，标记completed后汇总短路径成品
python -X utf8 scripts/publish_content.py "<run_dir>"
```

可直接复制的完整Prompt：[学习](prompts/standalone/learning.txt)、[博客](prompts/standalone/blog.txt)、[汇报](prompts/standalone/report.txt)、[小红书](prompts/standalone/rednote.txt)；明确只要图时用[只图入口](prompts/standalone/diagram.txt)。

Prompt规则源是 `prompts/common.txt` 和 `prompts/scenes/<scene>.txt`。修改公共源或场景规则后运行 `python -X utf8 scripts/export_prompts.py` 刷新全部独立稿，或用 `--scene report` 仅刷新该场景；不要直接改standalone造成规则分叉。准备脚本组合基础规则，AI负责读材料、策划和制作。`render_content.py` 产出 `index.html`、`qa.json`，report/rednote默认导出固定页PNG，diagram导出所选图；learning/blog只有显式 `--export-images` 才额外导出图片。可用 `--browser-executable` 复用指定Chromium；隐藏演示页需HTML提供全局激活函数并传 `--activate-hook activateContentExport`，详见统一流程。learning/blog的 `preview.png` 仅作首屏检查，不是整篇长图。

可复用的四场景源码骨架及构建命令见[模板使用](references/content-workflow.md#可选复用源码模板)。模板示例用于展示结构，正文仍需根据实际材料制作。

固定页标记 `data-export-page`，目录/导航等控件标记 `data-export-ui`，只图入口标记 `data-export-figure`。HTML需要资源内嵌并能直接离线打开，PNG不能依赖互动才看见条件。

`publish_content.py` 要求 `run.json` 状态 `completed` 与 `qa.passed`，将成品汇总到 `output/<短名>/` 并保留旧交付。rednote要求标题与摘要配文，其它场景不强制。发布仅指本地成品汇总。完整步骤见[统一流程](references/content-workflow.md)，内容结构与验收见[场景说明](references/content-scenes.md)，输入与版本见[工作区](references/workspace.md)。

## 视觉与质量

新四场景使用暖石白 `#F7F8F5`、正文 `#283331`、墨青 `#285F62` 与对照灰紫 `#775B7B`。中文优先MiSans；源码模板构建器会按实际字符内嵌本地Noto Sans SC缓存的子集作为离线回退，数学用可靠公式字体，代码等宽。字体包按需下载，不纳入Git；字体栈和资源存在不代表实际字体已正确显示，需查看实际输出。

先确定主线、理解障碍和图解选点，再制作。核心状态、执行路径、shape映射、数量/方向/尺度与几何关系用实际解释图，不用装饰图冒充证据。重要论断就近给来源，教学构造明确标注。必须看成品与截图，修正公式、标签、边界、字体及交互问题；机器QA不能替代技术和视觉判断。

本轮四场景独立试作使用同一在线Softmax固定材料，并完成对应浏览器检查及修正。该试作不证明任意材料自动生成均通过，也没有验证生图或模型API自动调用；每个新任务仍须重新检查。

## 环境与安装

```bash
git clone https://github.com/highting/rednote-skill.git
cd rednote-skill
python -m pip install -r requirements.lock.txt
python -m playwright install chromium-headless-shell
# 使用四场景源码模板时下载默认中文字体缓存；也可改用 --font 指定已有字体
python -X utf8 scripts/download_content_fonts.py
```

新脚本需要Python 3.10或更新版本。优先复用已有依赖、虚拟环境及浏览器，环境细则见[环境说明](references/environment.md)。本次改造发生在GitHub仓库源码，不表示已安装到个人技能目录或发布新插件版本。仓库保留 `.claude-plugin/` 元数据与 `skills/rednote-render-skill/SKILL.md` 插件入口；实际安装/加载遵循所用客户端及对应仓库版本。

运行前用当前checkout的 `--help` 核对参数。回归检查：

```bash
python -X utf8 -m unittest discover -s tests -v
```

## 旧入口兼容

旧Markdown → 小红书路径保留：

```bash
python -X utf8 scripts/prepare_blog.py "blogs/论文阅读/Hyperball" --mode html
python -X utf8 scripts/rednote_render.py "<work_entry>" --math katex --save-html -o "<artifact_dir>"
python -X utf8 scripts/publish_blog.py "<run_dir>"
```

旧 `rednote_render.py` 继续使用academic等现有主题、自动分页及KaTeX资源，默认3:4、1080×1440 CSS px、DPR2。旧参数见[params](references/params.md)，旧[HTML流程](references/html-mode.md)和[生图参考](references/image-mode.md)只在兼容入口或明确选择时适用。academic的暖米色、蓝橙与禁白约定不会覆盖新scene的暖石白默认。已有原稿和旧产物保留。

## 目录

| 路径 | 内容 |
|---|---|
| `inputs/`、兼容 `blogs/` | 分类/主题/原稿与附件 |
| `prompts/common.txt` | 公共可靠性、图解、视觉与交付规则 |
| `prompts/scenes/` | 各场景独立任务规则 |
| `prompts/standalone/` | 公共源＋场景规则的可复制完整稿 |
| `scripts/export_prompts.py` | 刷新独立稿，支持指定scene或output-dir |
| `scripts/prepare_content.py` | 新工作目录与基础任务Prompt |
| `scripts/download_content_fonts.py` | 按需下载并校验中文字体，缓存受Git忽略 |
| `scripts/build_content_template.py` | 将四场景源码骨架、本地中文与数学资源构建为离线HTML |
| `scripts/render_content.py` | HTML检查与场景PNG导出 |
| `scripts/publish_content.py` | completed/QA门槛及短路径汇总 |
| `output/_work/` | source/work/delivery、run.json与检查记录 |
| `output/<短名>/` | 最新可直接打开的成品 |
| `references/` | 流程、场景、兼容与环境说明 |
| `assets/`、`demos/` | 旧主题、离线数学资源与示例 |
| `skills/` | 插件技能入口 |
| `tests/` | 回归测试 |

MIT License © 2026 Bakameow. Original work by ZhangJia (comeonzhj).

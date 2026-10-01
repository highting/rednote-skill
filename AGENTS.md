# 内容制作工作区

本仓库支持四个独立内容场景：`learning` 学习长文、`blog` 技术博客、`report` 技术汇报、`rednote` 小红书图文；`diagram` 仅用于明确的只图请求。项目执行前完整读取根目录 `SKILL.md`、`references/workspace.md` 和 `.codex/error-notebook.md`（若存在），新流程再读 `references/content-workflow.md` 与选定场景说明。

- 新输入入口是 `inputs/<分类>/<主题>/`；保留 `blogs/<分类>/<主题>/` 作为兼容输入，不移动或覆盖用户原稿。用户仅给主题名时在这两个入口定位，唯一匹配直接处理；同名或无法判断主稿时才询问。
- 先选择场景，再选择辅助图模式。`html` / `images` 只决定合适的辅助图用 HTML＋SVG/程序图或可用生图工具，不决定正文形态、页数或交付目标。精确数值、shape、公式、算法状态与几何关系使用程序图；正文始终由可靠HTML排版。
- 新流程用 `scripts/prepare_content.py <输入目录> --scene <场景> --mode html` 建立 `output/_work/.../{source,work,delivery}/` 和 `run.json`。`source/` 为原始快照，制作发生在 `work/`，`delivery/` 是检查后的成品暂存。新请求建新工作目录，同次修正复用。
- 读取 `prompts/common.txt` 与 `prompts/scenes/<scene>.txt`，结合本次材料与约束形成任务Prompt。`prompts/standalone/` 保存各场景可复制完整稿；维护源规则后用 `python -X utf8 scripts/export_prompts.py` 重新导出，不直接改派生稿。AI按场景制作完整、自包含、可离线打开的 `index.html`，保留源稿、生成脚本及实际图解；不要只输出大纲或图的提示词。
- 用 `scripts/render_content.py <index.html> --scene <场景> --output-dir <delivery>` 检查与导出；可用 `--browser-executable` 指定已有浏览器。`report`、`rednote` 默认导出固定页PNG；`learning`、`blog` 默认只交HTML与桌面检查，只有显式 `--export-images` 才导出额外图片。`diagram` 按标记导出所选图。
- 固定页用 `data-export-page`，导航、目录、备注控件等用 `data-export-ui`，只图入口用 `data-export-figure`。导出时静态内容必须完整，不能靠交互显示必要条件。默认隐藏的演示页需提供全局激活函数并传 `--activate-hook activateContentExport`，不能假定渲染器知道翻页接口。
- 实际查看HTML与相应最终PNG，核对技术、主线、图解、公式、中文字体、页界和交互。只有检查完成才将 `run.json` 标记 `completed`；`scripts/publish_content.py <run_dir>` 要求 `completed` 与 `qa.passed`，更新 `output/<短名>/` 并保留旧交付。不要手改通过结果绕过失败。
- `rednote` 的选定范围必须能只按图片顺序独立理解主线，标题和配文不能补缺失正文；它交 `标题.txt` 与 `配文.txt`，配文只作摘要。其它场景不强制发布文案，不将文章切片冒充汇报或学习文档。
- 四场景新默认为暖石白 `#F7F8F5`、正文 `#283331`、墨青 `#285F62`、对照灰紫 `#775B7B`，中文优先MiSans及可用中文无衬线字体。旧 `academic` 的暖米色、禁纯白及3:4约定仅适用于旧入口或用户明确选择该主题，不能覆盖明确新scene的默认。
- `prepare_blog.py`、`publish_blog.py`、`rednote_render.py` 保留旧Markdown→小红书兼容路径。旧说明见 `references/workspace.md`、`html-mode.md`、`params.md`；与新场景冲突时按新场景文档及用户指令执行。
- `assets/`、`scripts/`、`references/`、`skills/`、`tests/` 是公共资源，不放单篇原稿或临时安装文件。此次维护属于GitHub仓库源码改造，不表示已安装到个人技能目录。脚本准备目录、组合Prompt、检查或截图，不自动调用AI、生图模型或发布社交平台。

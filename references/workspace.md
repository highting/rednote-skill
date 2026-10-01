> **路由说明：本页记录旧Markdown→小红书/academic兼容流程。** 新请求先按 `learning`、`blog`、`report`、`rednote` 选择场景，见[统一流程](content-workflow.md)与[场景说明](content-scenes.md)。新输入是 `inputs/<分类>/<主题>/`，现有 `blogs/` 也可输入新流程。旧正文全转PNG、3:4、暖米色禁白、字体及配文约定仅用于旧入口或明确选择academic，不覆盖新scene的暖石白默认。`html/images` 只选辅助工具；精确数值、shape、算法状态、公式与几何关系仍用程序图，不因images模式强制生图。

# 长期博客工作区

## 日常使用

把博客文件夹拖入 `blogs/` 下合适的分类，正文、图片和附件一起放入，保持相对路径。已建 `机器学习`、`论文阅读`、`工程实践`、`待分类`；可以自行新增分类，也可以在分类下继续分子类。博客名可用中文和空格，无需填写配置文件。

例如：

```text
blogs/
└── 机器学习/
    └── Hyperball/
        ├── main.md
        └── images/
            └── geometry.png
```

在本项目中新建或继续会话，直接说：

> 把 blogs/机器学习/Hyperball 做成可连续阅读的小红书图片笔记，正文用 HTML，辅助图用 HTML＋SVG，配文写摘要。

> 把 Hyperball 用生图模式做成小红书图文：正文仍用 HTML 排成图片，辅助解释图用 ImageGen，配文只作摘要。

> 给 Hyperball 生成两张辅助解释图，并注明博客中的插入位置。

> 把 Hyperball 做成一张一图流。

博客名唯一时可以只说名字；重名时提供分类或完整相对路径。未指定模式默认 HTML。拖入本身不会触发生成，需要在会话中发出要求。自动读取这些约定的前提是会话工作目录在本项目中。

## 输入与正文选择

推荐正文名 `main.md`，也支持保持现有文件名。准备脚本优先识别博客根目录的 `main.md`、`article.md`、`index.md`（按此顺序）；否则寻找唯一的 Markdown、Word、PDF 或 HTML 正文。存在多份候选时，可由用户明确指定正文，或由代理阅读后确定实际主稿，通过 `--entry` 传入相对于博客文件夹的路径；确实无法判断才询问。

Word、PDF、HTML 输入先用对应工具读取，并将供渲染的 Markdown 整理到工作目录的 `work/`。准备脚本不负责格式转换、排版或生图。完整正文不可误当作图片附件忽略。图片引用到文件夹外部时，应在 `work/` 中补齐资源并调整工作稿引用；交付资源必须能离开原机器使用。

## 目录与版本

```text
项目根目录/
├── blogs/                         # 日常拖入：分类/博客名/正文和附件
├── output/
│   ├── Hyperball/                 # 用户直接打开的最新成品
│   │   ├── 标题.txt
│   │   ├── 配文.txt
│   │   ├── card_1.png             # 按页序放完整图片，不再多套 images/
│   │   ├── card_2.png
│   │   ├── 预览.html              # 同页展示标题、配文和图片
│   │   └── html/                  # 可离线打开的 HTML 排版源页及资源
│   ├── _work/Hyperball/
│   │   └── 20260914-153000-123456-html/
│   │       ├── source/            # 原始材料快照，不修改
│   │       ├── work/              # 正文排版稿、SVG、图面说明和检查材料
│   │       ├── delivery/          # 标题、配文与图片的成品暂存
│   │       ├── previous-deliveries/ # 更新短路径前保留的旧交付（如有）
│   │       ├── run.json           # 输入、路径和执行状态
│   │       └── delivery.md        # 来源、页序和检查记录
│   ├── _archive/                  # 整理前的产物和检查材料
│   ├── validation-python/         # 已有本机验证依赖
│   └── validation-browsers/       # 已有本机验证浏览器
├── demos/                         # 主题和图形示例
├── assets/                        # 公共模板、主题、KaTeX
├── scripts/                       # 准备和渲染脚本
├── references/                    # 长期流程说明
├── skills/                        # 插件入口
└── tests/                         # 回归测试
```

两种模式均将完整 PNG 序列、标题与配文放在 `output/<短名>/` 的同一层。默认短名使用博客文件夹名，冗长时用 `--name` 指定清楚的短名，如 `Hyperball`。不同博客不得共用同一短名，有重名时增加简短限定词。正文一律由 HTML 渲染；模式只决定非正文视觉使用 HTML＋SVG 或 ImageGen。

每次新请求在 `_work/` 下建立带时间戳和模式的独立工作目录，同次修正复用它。新的结果完成检查后才更新短路径；现有成品先留存到本次工作目录的 `previous-deliveries/`，再完整复制本次成品，避免页数减少后混入旧图。用户要求两套时用 `Hyperball-HTML`、`Hyperball-生图` 等短名区分，两套各自将图片、标题和配文放在一起。两套共用正文 PNG、HTML 源页、页序和配文，只替换辅助图。

## 代理执行约定

先确定博客和正文，再从项目根目录运行（Python 不在 PATH 时使用当前环境提供的解释器绝对路径）：

```powershell
python -X utf8 scripts/prepare_blog.py "blogs/机器学习/Hyperball" --mode html --name Hyperball
# 多正文时明确入口，路径相对于博客文件夹
python -X utf8 scripts/prepare_blog.py "blogs/机器学习/Hyperball" --entry "正文/技术稿.md" --mode images --name Hyperball-生图
```

脚本返回 `run_dir`（独立工作目录）、`artifact_dir`（本次成品暂存）、`delivery_dir`（简短交付入口），并复制完整博客目录到 `source/` 和 `work/`，保持内部相对引用。使用 `work_entry` 作为工作稿入口；转换格式后在 `run.json` 更新该字段。

两种模式均先整理能独立读完的正文，规划正文页和辅助解释图。正文渲染稿准备好后运行渲染器，输出到本次 `artifact_dir`，分批渲染也可先放 `work/` 再按共同页序汇总：

```powershell
python -X utf8 scripts/rednote_render.py "<work_entry>" --math katex --save-html -o "<artifact_dir>"
```

最终图片按页序命名为 `card_N.png`（明确需要独立封面时可加 `cover.png`）。生图模式只对非正文视觉调用相应工具；分批生成不能覆盖其他页。HTML 页及资源放在 `artifact_dir/html/`；正文排版稿、图面说明和提示词留在 `work/`。按[发布标题与配文规则](content-plan.md#发布标题与配文)写好 `artifact_dir/标题.txt` 和 `artifact_dir/配文.txt`：标题不使用第一人称，直接表达主题或核心论点；配文用作者第一人称，轻松自然且只作摘要。工具生成文件必须本地化。

准备后 `run.json` 状态为 `prepared`，制作时改为 `generating`；完整正文图片、辅助图、标题和配文完成检查后才标记 `completed`。记录各页类型、制作方式和实际检查结果，来源与页序放在工作目录的 `delivery.md`。然后执行：

```powershell
python -X utf8 scripts/publish_blog.py "<run_dir>"
```

脚本生成包含标题、配文和图片的 `预览.html`，将成品整体汇总到 `delivery_dir`，并更新交付记录。最终回复优先链接 `output/<短名>/`、`标题.txt`、`配文.txt` 或 `预览.html`，不要把中间 `work/` 路径作为发布材料入口。仅请求辅助图或一图流时按用户范围准备交付文案，不扩写整篇正文。

## 历史材料与维护

早期的 `hyperball-xhs`、主题产物和 HTML 检查材料在 `output/_archive/2026-09-14/`；旧版本仍可保留在 `output/blogs/`，不再将该深层路径作为新的交付入口。其中 `hyperball_xhs.md` 是已有改写稿，不自动当作博客原稿。历史检查脚本只是当时的复现材料，内部旧路径执行前需调整；已有版本可补上 `delivery_dir` 后用汇总脚本建立短路径成品。

已有验证依赖暂存位置保留，避免破坏当前可用环境。后续新依赖遵循 `references/environment.md`，使用用户环境或 `.venv/`，不要继续混入正式产物。

`output/` 已被 `.gitignore` 忽略；`blogs/` 原稿可纳入版本管理。Git 忽略不等于备份：长期备份应覆盖原稿、需要保留的工作版本和短路径成品。公共模板和主题统一维护，单篇博客内容在其工作目录处理，完成后更新对应短路径交付。

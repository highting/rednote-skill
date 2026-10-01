# 新场景工作流：材料 → 场景Prompt → 离线HTML → 检查/PNG → 成品

本流程适用于 `learning`、`blog`、`report`、`rednote`，及用户明确只要图时的 `diagram`。旧Markdown→小红书流程见[工作区兼容说明](workspace.md)和[旧参数](params.md)。新默认不由旧academic主题决定。

## 1. 读取材料并准备独立工作目录

原稿放在 `inputs/<分类>/<主题>/`；现有 `blogs/` 也兼容。保持正文、图片和附件的相对路径，正文入口有歧义时先阅读判断，确实不能判断再询问。

```bash
python -X utf8 scripts/prepare_content.py "inputs/机器学习/在线Softmax" --scene learning --mode html
# 现有材料不用搬迁
python -X utf8 scripts/prepare_content.py "blogs/论文阅读/Hyperball" --scene report --mode html
```

准备脚本建立本次 `output/_work/.../`，包含：

| 路径 | 用途 |
|---|---|
| `source/` | 完整原始材料快照，不编辑 |
| `work/` | 工作副本、源稿、图解、生成脚本、任务Prompt与检查说明 |
| `delivery/` | 成品暂存：index.html、qa.json与场景要求的PNG/文案 |
| `run.json` | 输入、scene、mode、路径和执行状态 |

新请求新建工作目录，同次修正复用。脚本返回的路径与本次 `run.json` 是运行路径依据，不手写覆盖旧版本。任务Prompt写在 `work/任务Prompt.txt`。可用 `--entry` 指定主稿、`--name` 指定单层短名、`--topic` / `--scope` 记录主题与范围；同主题要并存多个场景时给各场景不同短名。准备不负责阅读PDF、转换Word或制作正文；先用合适工具读实际材料，转换稿留在 `work/`，原稿保留。

## 2. 组合规则并先策划

读取 `prompts/common.txt` 与 `prompts/scenes/<scene>.txt`，结合实际材料、读者、目的、范围、时间/页数及用户约束，形成完整任务Prompt。准备脚本负责组合基础规则与主题、范围、材料路径；AI负责理解材料、补齐任务输入和制作。不要把不同scene文件都拼进同一次任务，导致约束互相覆盖。

独立可复制的完整稿在 `prompts/standalone/learning.txt`、`blog.txt`、`report.txt`、`rednote.txt`；只图窄入口另有 `diagram.txt`。这些是公共源与场景规则的组合产物，不是第二套规则源。修改源规则后运行：

```bash
python -X utf8 scripts/export_prompts.py
# 仅刷新一个场景
python -X utf8 scripts/export_prompts.py --scene report
```

脚本默认写 `prompts/standalone/`，也支持 `--output-dir`；它不调用模型。不要只修改standalone导致规则漂移。

制作前简要记录主线、读者卡点和图解选点表：卡点→图展示的关系→插入位置→制作方式→完成状态。图是解释关系的实际成品；文字/小表更清楚时给具体理由，不按章节凑数量。

`--mode html` 默认用程序图；`--mode images` 允许适合的辅助视觉用可用生图工具。两种模式都由HTML排正文。精确数值、shape、算法状态、公式及几何仍用程序图；模式不是把所有图交给同一工具的命令。

## 3. AI制作完整自包含HTML

在 `work/` 制作 `index.html`，保留源稿、生成脚本和必要资产。所有必需CSS、JavaScript、字体、数学及图片内嵌，确保离开原机器也能直接离线打开。资源确实太大且用户接受离线包时可另交完整包，不能称其为单文件自包含；本统一渲染器仍只接受自包含入口，不会替带外部引用的HTML自动打包或内联。

公式先可靠渲染，中文正文、图内文字、代码注释和数学中的中文均有可用字体回退。图形CSS只作用于自有SVG，不覆盖KaTeX。真实证据与教学构造明确区分；制作说明、环境记录、图解表和验收记录另附。

按scene组织内容，不用渲染脚本替代策划：learning/blog是连续阅读文档；report为每页一个讲解任务并含备注；rednote在图片选定范围内闭环；diagram只做明确请求的图。

### 可选复用源码模板

`assets/content/` 保存四个场景的HTML骨架及共享CSS/JS。AI可依据本次材料制作正文片段，再复用骨架：

```bash
python -X utf8 scripts/build_content_template.py --scene learning \
  --output "<run_dir>/work/index.html" --title "本次主题" \
  --body-file "<run_dir>/work/body.html"
```

`--body-file` 是已经写好的可信HTML片段，不是Markdown、Prompt或自动撰稿入口；learning/blog片段包含连续正文的章节与图，report/rednote片段包含明确的 `data-export-page` 页面。必要脚本可直接制作完整HTML。省略片段时只生成明确标注的源码模板示例，不能将示例文字当成已完成的主题内容。

构建器内嵌本地KaTeX资源及数学字体；默认按HTML实际字符选取本地Noto Sans SC缓存的WOFF2子集，作为正文、SVG、代码和数学中文的离线回退。字体包不纳入Git；首次使用模板先运行 `python -X utf8 scripts/download_content_fonts.py` 下载并校验，或使用 `--font /path/to/licensed-font.woff2`。下载只在显式执行时发生，成品内嵌所需字体，离线阅读无需再下载。MiSans/微软雅黑仍优先使用。字体须允许嵌入；提供资源不能代替真实字形与混排检查。来源/许可及复用本地包的方法见 `assets/vendor/noto-sans-sc/`。

骨架包含两级学习/博客目录与稳定开合、汇报目录/翻页/讲者备注，以及固定画幅图文。它们提供起点，不能自动解决长正文、复杂图或所有字体的排版；每次填入实际内容后重新检查并调整。

### 导出标记

```html
<!-- report/rednote固定页；尺寸由页面CSS可靠设置 -->
<section data-export-page>完整页面与必要条件</section>
<!-- 页外目录、翻页、备注入口等，导出时不进入图片 -->
<nav data-export-ui>交互控件</nav>
<!-- diagram独立图：图与必要短图注/条件一起标记 -->
<figure data-export-figure>实际解释图</figure>
```

导出固定页时各页应能在静态状态完整显示。演示页面若默认隐藏非当前页，需提供明确的全局激活函数，并用 `--activate-hook` 指定其名称；函数接收零基索引的 `{index, scene, element}`，负责把对应页设为可见并同步其状态/ARIA。渲染器不会猜测演示框架的翻页接口，隐藏目标会检查失败。它在激活后移除缩放并隐藏其它导出目标，按标记逐页截图。只图导出应包含独立传播所需的标签与条件，不能截掉图注。控件标记不应用于正文条件或必要证据。

## 4. 统一检查与导出

```bash
python -X utf8 scripts/render_content.py "<run_dir>/work/index.html" \
  --scene learning --output-dir "<run_dir>/delivery"

python -X utf8 scripts/render_content.py "<run_dir>/work/index.html" \
  --scene report --output-dir "<run_dir>/delivery" \
  --browser-executable "/path/to/chromium" --activate-hook activateContentExport

# learning/blog只有用户明确需要图片时开启
python -X utf8 scripts/render_content.py "<run_dir>/work/index.html" \
  --scene blog --output-dir "<run_dir>/delivery" --export-images
```

`render_content.py` 将入口成品与检查结果放到输出目录，产出 `index.html`、`qa.json`，并按场景输出PNG。`report` 示例假设HTML已定义 `activateContentExport`；所有目标原本可见时可省略该参数。默认DPR为1，可显式 `--dpr`；report默认1280×720、rednote默认1080×1440 CSS px，可用 `--width` / `--height` 与用户约定画幅一致。默认固定页/图图片命名为 `page-01.png`、`page-02.png` 等；learning/blog保留 `preview.png` 首屏检查截图，不代表整篇长图。默认导出规则：

| scene | 默认图片 | 验收范围 |
|---|---|---|
| learning/blog | 不导出额外长图；显式 `--export-images` 才导出 | HTML桌面分区检查，核心图、公式/代码、目录与结尾 |
| report/rednote | 导出 `data-export-page` 固定页 | 全部PNG及对应HTML；report交互/备注，rednote手机尺寸 |
| diagram | 导出 `data-export-figure` | 所选图、边界、条件和可读性 |

新脚本使用Python 3.10或更新版本。优先复用已有Python依赖和浏览器；只有实际缺口才按[环境说明](environment.md)补齐，不重复安装或引入通用前后端框架。浏览器可通过可选 `--browser-executable` 指定。

机器检查关注可检测的加载、边界与导出问题；必须实际打开HTML并查看截图/PNG，核对字体、公式、技术、图意、遮挡、页界、锚点和实际交互。不要用元素数或成功日志代替视觉检查。发现硬错误先修，改后重新渲染；记录只写实际做过的项目，未验证项明确标记。

## 5. 完成与短路径发布

完成所选scene的正文、图、来源和实际检查后，在工作记录中注明结果，再将 `run.json` 状态设为 `completed`。`rednote` 还需在 `delivery/` 放 `标题.txt` 与 `配文.txt`；其它场景不强制这两个文件。

```bash
python -X utf8 scripts/publish_content.py "<run_dir>"
```

发布脚本要求 `completed` 和本次 `qa.json` 的 `passed`，核对scene、主HTML哈希与列出的PNG，原稿快照也必须保持不变，否则拒绝汇总。修正真实问题后重跑检查，不改结果绕过门槛。成品更新到 `output/<短名>/`，保留原有交付，避免页数变少后残留旧图。最终交付优先指向该短目录的 `index.html` 与场景成品，源稿/制作记录另附，不让用户进入 `work/` 寻找正文。

这里的“发布”是本地成品汇总，不向GitHub、社交平台或个人技能目录上传。此仓库改造提供规则和工作流；AI与生图调用由实际运行环境承担，脚本没有通用模型/API自动调用能力。

## 旧入口兼容

`prepare_blog.py`、`rednote_render.py`、`publish_blog.py` 保持既有Markdown分页PNG路径与academic主题。已有原稿、主题示例和旧产物不被新流程覆盖。旧文档中的“所有正文必须PNG”“默认3:4”“暖米色禁白”是旧路径约定，不能应用到新learning/blog/report场景或明确的暖石白scene默认。

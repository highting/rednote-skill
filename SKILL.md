---
name: rednote-render-skill
description: Create learning documents, technical blogs, presentation reports, and RedNote image posts from source material. Plan each scene separately, produce portable offline HTML, and validate or export PNG pages with optional supporting visuals.
---

# 内容制作与 HTML → PNG

先按读者与使用目的选择 `learning`、`blog`、`report` 或 `rednote`，再组织对应成品。四种场景共享技术准确、图解选点、离线资源和实际渲染检查；它们有各自的内容主线、密度、导航和交付要求。明确只要局部解释图时使用窄入口 `diagram`，不要扩成整篇。

本技能名保持 `rednote-render-skill` 以兼容现有插件入口，能力已扩展到四场景。根文件是规范入口，插件条目引用本文件。仓库源码变更不等于个人技能安装，也不等于已部署新的插件版本。

## 选择场景

| 目的 | scene | 成品与默认验收 |
|---|---|---|
| 系统理解概念、机制与必要推导 | `learning` | 连续学习HTML、目录与桌面分区检查；默认不额外长图 |
| 面向读者独立阅读和分享技术论点 | `blog` | 连贯博客HTML、就近来源与桌面检查；默认不额外长图 |
| 在有限时间让团队形成判断 | `report` | 16:9演示HTML、可直达目录、键盘翻页、关联讲者备注及逐页PNG |
| 让读者按图片顺序理解选定主题 | `rednote` | 3:4有序PNG、离线HTML、标题与摘要配文 |
| 用户明确只请求局部图或总览图 | `diagram` | 标记的独立解释图及其源文件；遵从指定范围和数量 |

具体默认、内容策划与验收见[场景说明](references/content-scenes.md)。完整可复制Prompt见 `prompts/standalone/{learning,blog,report,rednote}.txt`，窄入口另有 `diagram.txt`；维护时改公共源/场景源后运行 `python -X utf8 scripts/export_prompts.py` 刷新，不另改派生稿。已有明确读者、时长、范围或格式时沿用，不重复确认。主题无法确定、关键材料缺失，或冲突会改变主结论时才询问。

## 选择辅助图模式

- `--mode html`：默认。适合用SVG、Canvas或程序绘图表现精确关系。
- `--mode images`：合适的具象场景、空间直觉或类比可使用环境中实际可用的生图工具，完成后检查图意；正文仍由HTML可靠排版。

模式只影响辅助视觉制作工具，不切换场景、不压缩正文，也不强制所有图都用同一工具。精确数值、张量shape、算法状态、公式、几何与连接关系必须由可核对的程序图承担，即使选择了 `images`。生图工具不可用时如实说明，不能把网页截图称为模型生图。只生成Prompt不算生成图片。只有用户明确要求两套比较时才制作两套，保持正文、证据口径和语义顺序一致。

## 新流程

1. 按[工作区](references/workspace.md)定位 `inputs/<分类>/<主题>/`，也接受现有 `blogs/`。读取实际正文、图片及来源；原稿不变，工作副本单独制作。
2. 按[统一流程](references/content-workflow.md)运行 `prepare_content.py`，读取 `prompts/common.txt` 与 `prompts/scenes/<scene>.txt`，把材料、目的和约束纳入任务Prompt。
3. 先确定内容主线、读者卡点与图解选点表，再制作完整自包含 `index.html`。保留生成源稿/脚本与必要资产；正文不混入制作说明、环境记录或评审清单。
4. 用 `render_content.py` 检查离线HTML，并按scene导出固定页/图PNG。实际查看HTML、截图和需要交付的全部图片；修改后重新渲染。默认隐藏的汇报页提供全局 `activateContentExport({index, scene, element})`，并向渲染器传 `--activate-hook activateContentExport`。
5. 完成后记录来源、图解、实际检查与边界，标记 `run.json` 的 `completed`。用 `publish_content.py` 通过 `completed`、`qa.passed` 门槛，交付 `output/<短名>/`。

脚本只准备、组合规则、检查与截图，不自动撰稿、不调用生图API，也不上传社交平台。未实际生成或验证的项目不能写成通过。`qa.json` 的机器检查不能替代人工查看图意、论证和实际字体。

## 技术与图解

先读材料，重要论断给实际来源及可得的章节、公式或代码位置；区分材料事实、教学构造、自行推导与推断。核对变量、条件、维度、shape、状态和数量尺度，不虚构实验、收益或代码路径。沿概念依赖或执行路径组织，不机械套“旧方法失败→新方法更好”。

图解先选理解障碍，再制作。结构、前后状态、算法执行、shape映射、数量/方向/尺度/几何及真实对比是核心段落时，默认需要解释图；文字或小表更清楚时在制作记录给具体理由。一个图回答一个问题，展示起点、关键中间状态、结果及映射，不能把封面、图标或彩色文字框算机制图。数字与图共用同一数据；对照使用一致尺度和条件。真实证据图不改色，教学构造明确标注。

公式源稿行内用 `\( ... \)`，独立用 `\[ ... \]`，由KaTeX或可靠MathJax实际渲染；复杂式断行，不露源码。正文、代码注释与公式中的中文都要有可用中文字体回退，不只设置正文font-family。使用源码模板时，首次显式运行 `python -X utf8 scripts/download_content_fonts.py` 获取默认中文字体缓存，或以 `--font` 指定允许嵌入的本地字体；字体包不纳入Git，成品内嵌所需子集。图形CSS限定自有SVG，避免破坏数学排版。

## 新场景视觉

暖石白背景 `#F7F8F5`，分组底 `#EEF1EC`，正文 `#283331`，次要文字 `#63706D`，边界 `#D8DFD9`，墨青 `#285F62`，对照灰紫 `#775B7B`，浅填充 `#E5EFEC` / `#EFE8F0`。中文优先MiSans，回退微软雅黑、合法可用的中文无衬线字体；数学用专业字体，代码等宽。常规文字对比度至少4.5:1。

先建立对象与颜色/线型映射，同一语义跨图沿用；不用一种颜色表示无关含义，不只靠颜色区分。靠尺度、对齐、留白、图大小和节奏建立层级，轻量分组只用于不同语义。避免满屏同款卡片、巨大空白封面、霓虹渐变、纸纹、泛黄、厚阴影或装饰三维。

旧 `academic` 是已有Markdown入口的兼容主题，保留暖米色、蓝橙及既有字体设置。旧说明中的禁白、3:4或默认academic不覆盖明确新scene；用户明确指定主题/字体时遵从用户。

## 交付与兼容

新成品必须能直接离线打开，内嵌资源；资源过大时交完整离线包并说明入口。`learning/blog` 默认HTML与桌面检查，额外图片必须显式请求；`report/rednote` 逐页检查PNG；`diagram` 仅检查所选图。场景验收及导出标记见[统一流程](references/content-workflow.md)。

`rednote` 的图片在选定范围内必须独立串起问题、必要解释、条件与结论。标题直接表达主题或主张，不用第一人称或标题党；配文用自然的作者第一人称，只作摘要，不编造经历，不补缺失正文。其它场景不强制标题/配文文件。

旧 `prepare_blog.py` → `rednote_render.py` → `publish_blog.py` 仍可按原有Markdown流程使用，细则见[旧HTML流程](references/html-mode.md)、[旧参数](references/params.md)、[旧生图参考](references/image-mode.md)。它们保留兼容功能，不作为新四场景默认路由。

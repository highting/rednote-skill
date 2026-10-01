> **路由说明：本页记录旧Markdown→小红书/academic兼容流程。** 新请求先按 `learning`、`blog`、`report`、`rednote` 选择场景，见[统一流程](content-workflow.md)与[场景说明](content-scenes.md)。新输入是 `inputs/<分类>/<主题>/`，现有 `blogs/` 也可输入新流程。旧正文全转PNG、3:4、暖米色禁白、字体及配文约定仅用于旧入口或明确选择academic，不覆盖新scene的暖石白默认。`html/images` 只选辅助工具；精确数值、shape、算法状态、公式与几何关系仍用程序图，不因images模式强制生图。

# 渲染参数

本脚本负责两种模式共同的 HTML 正文页，以及 HTML 模式的 SVG 辅助图：将整理后的连续正文、KaTeX 公式或 SVG 排版为页面，再逐页输出 PNG。它不调用 ImageGen。先按[图文组织规则](content-plan.md)整理文章并确定语义分页，不将正文压成辅助图文案。

```bash
python -X utf8 scripts/rednote_render.py cards.md --math katex --save-html -o "<artifact_dir>"
```

## 参数

| 参数 | 简写 | 作用 | 默认值 |
|---|---|---|---|
| `--output-dir` | `-o` | 图片输出目录 | 当前目录 |
| `--theme` | `-t` | 排版主题；其他主题仅显式指定 | `academic` |
| `--width` | `-w` | 页面宽度，CSS px | `1080` |
| `--height` | | 页面高度，CSS px | `1440` |
| `--dpr` | | PNG 像素密度，不增加内容容量 | `2` |
| `--math` | | `off` 或 `katex`，覆盖 front matter | 读取 `math` |
| `--save-html` | | PNG 之外在 `html/` 保留制作源文件 | 关闭 |
| `--format` | | `png` 输出图片；`html` 仅导出中间源文件 | `png` |

默认 3:4 页面、1080×1440 CSS px，DPR 2 得到 2160×2880 PNG。输出 `cover.png`（含封面标题时）及 `card_N.png`。无需额外封面时不设置封面 front matter。

PNG 和 HTML 都校验固定画幅；过高块及可检测的横向溢出会报错，须精简或重排。不能裁内容、缩字或增加图片高度绕过检查。自动分页保留代码、公式、表格和 SVG 等完整块，内容规划仍需保证每张图有完整图意；`---` 只是分隔线，不是手动页界。

`--save-html` 在 PNG 之外保存 `html/index.html`、`html/pages/` 及必要资源。`--format html` 仅单独检查源文件，不完成小红书配图交付。保存的 HTML 为静态页面，保留数学和图形 DOM 并移除脚本；修改后重新渲染 PNG。页面源文件使用系统中文字体，字体不会自动打包。

本地图片路径相对于渲染稿目录解析，保存 HTML 时普通图片会内联；复杂外部 SVG／CSS 依赖需在准备阶段整理为完整本地资源。不要把有配套资源的 `index.html` 称为自包含单文件。

## 主题与常用命令

默认直接采用 `academic`，不需要推荐或比较主题。原有主题资源保留，每次只加载选中 CSS；仅用户指定其他主题时读取 [STYLES.md](../STYLES.md) 对应部分。主题改变视觉风格，不改变图片交付、固定画幅和几何准确性的要求。

```bash
# 默认技术图文：HTML＋SVG → 分页 PNG
python -X utf8 scripts/rednote_render.py cards.md

# 几何图示例，同时保留制作源文件
python -X utf8 scripts/rednote_render.py demos/academic.md --save-html -o output/geometry

# 对应比较示例
python -X utf8 scripts/rednote_render.py demos/academic-comparison.md -o output/comparison

# 显式指定旧主题时仍可使用
python -X utf8 scripts/rednote_render.py cards.md -t sketch -o output/sketch
```

## 渲染稿

```yaml
---
title: "封面标题"       # 仅需要额外封面时填写，建议不超过 15 字
subtitle: "必要副标题"  # 可省略
math: katex             # 可选，行内公式用 \(...\)，独立公式用 $$...$$
---
```

正文支持标题、段落、列表、引用、代码、表格、图片和内嵌 SVG。技术图不默认添加 Emoji 或标签。KaTeX 使用仓库内置资源，不依赖运行时网络。

## SVG 与数学标签

参考 `demos/academic.md` 和 `demos/academic-comparison.md`：

- `.figure-scene` 是相对定位容器，SVG 使用 `viewBox`。
- `.figure-label` 是同坐标系内的 HTML 数学标签，`left`、`top` 百分比表示标签中心；由 KaTeX 排版公式，不在 SVG `text` 内直接写 LaTeX。
- `.vector-primary`、`.vector-update`、`.vector-contrast` 对应蓝、青、橙；`.vector-reference` 为浅灰辅助线，`.geometry-mark` 为几何标记。
- `.figure-panel` 仅用于有意义分组；`.proposed`、`.updated`、`.baseline` 指定强调色，`.tint` 按需添加浅填充，普通说明保持墨灰。
- `.figure-grid` 默认单列；`.comparison` 用于对应比较，其他比例可设置 `style="--figure-columns: 3fr 2fr"`。

图形字号必须结合最终缩放核对。查看实际 PNG 并按手机尺寸复查；自动尺寸检查不能代替几何、标签和遮挡检查。

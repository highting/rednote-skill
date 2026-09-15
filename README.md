# RedNote-Render-Skill

将技术材料制作成可连续阅读的小红书 3:4 图片笔记。正文统一用 HTML 排成图片；辅助解释图等非正文视觉选择 HTML＋SVG 或 ImageGen。小红书配文只作摘要，默认采用浅暖米色背景的学术技术风格。

## 日常博客入口

将完整博客文件夹拖到 `blogs/<分类>/`，保留正文和配图的相对路径。例如 `blogs/机器学习/Hyperball/main.md`，再在本项目会话中说：

> 把 blogs/机器学习/Hyperball 用 HTML 模式生成，按项目规则输出。

或说“把 Hyperball 用图片模式生成小红书图文”。博客名唯一时可以省略分类；没有指定模式时默认 HTML。已建 `机器学习`、`论文阅读`、`工程实践`、`待分类`，可以自行新增分类。

成品统一放在 `output/<短名>/`，例如 `output/Hyperball/`：最终图片、`标题.txt`、`配文.txt`、`预览.html` 都在同一层，HTML 源页在 `html/`。中间材料与版本记录单独放在 `output/_work/`，不需要进入工作目录寻找配文。拖入后需发送生成要求，不会后台自动执行。

目录规则、版本说明和更多 prompt 见[工作区说明](references/workspace.md)。根目录 `AGENTS.md` 让后续本项目会话沿用这些约定；`scripts/prepare_blog.py` 准备目录与副本，`scripts/publish_blog.py` 在检查后汇总成品并保留旧交付。

## 两种模式

| 模式 | 内容处理 | 交付 |
|---|---|---|
| [HTML 模式](references/html-mode.md) | 连续正文用 HTML，辅助解释图用 HTML＋SVG | 正文与辅助图 PNG、发布摘要及源文件 |
| [生图模式](references/image-mode.md) | 正文仍用 HTML，辅助解释图用 ImageGen | 正文与辅助图 PNG、发布摘要及源文件 |

两种模式共用[图文组织规则](references/content-plan.md)：正文图片承载文章主线，辅助解释图穿插解释关系。发布标题和封面标题不使用第一人称，直接表达主题或核心论点；配文采用作者第一人称，轻松自然、只作摘要。两套比较共用正文页与配文，只更换非正文视觉。字体沿用项目设置，参考图默认只用于字号和间距。仅请求辅助图或一图流时遵从该范围；原稿保留，不要求默认逐字搬运。

调用示例：“正文用 HTML 排成图片，辅助图用 HTML＋SVG，配文写摘要”；“正文页用 HTML，辅助图分别做 HTML＋SVG 和生图两套，让我比较”；“不用 ImageGen，把这个主题做成一张 3:4 一图流”。

## 安装

### Claude Code Plugin（推荐）

```bash
# 添加 marketplace
/plugin marketplace add Bakameow/RedNote-Render-Skill

# 安装插件
/plugin install rednote-render-skill@Bakameow-RedNote-Render-Skill
```

安装后运行 `/reload-plugins` 即可使用。

### 手动安装

```bash
git clone https://github.com/Bakameow/RedNote-Render-Skill.git
cd RedNote-Render-Skill
python -m pip install --user -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements.lock.txt
python -m playwright install chromium-headless-shell
```

Python 包安装到当前用户环境，浏览器使用系统用户共享缓存。浏览器的大陆镜像配置、官方回退、MiSans 安装与已验证版本见 [环境说明](references/environment.md)。已有虚拟环境时省略 `--user`。

安装后运行 `python -X utf8 -m unittest discover -s tests -v` 执行回归测试，包含真实浏览器和离线公式检查。

---

## 特性

- **默认技术风格**：直接使用 `academic`，不要求每次选择主题；其他主题仅显式选择，详见 [STYLES.md](STYLES.md)
- **自动分页**：根据内容渲染高度拆分为多张卡片，代码块、表格和 SVG 尽量保持完整
- **技术内容支持**：内置 KaTeX 数学公式资源，并支持表格和内嵌 SVG
- **academic 主题**：浅暖米色卡片（`#FAF9F5`），单一学术蓝，橙色仅作必要对照，轻量几何和短标签；HTML 渲染中文优先微软雅黑，生图按 prompt 使用宋体／serif
- **Playwright 渲染**：高质量 HTML → PNG 输出
- **保留制作源文件**：可随 PNG 保存分页 HTML 与离线数学资源，便于后续修改和复现
- **独立生图流程**：按目的选择内容图片、辅助解释图和一图流

---

## 使用方法

```bash
python scripts/rednote_render.py <markdown_file> [options]
```

```bash
# 默认：academic 主题，HTML＋SVG 分页后导出 PNG
python scripts/rednote_render.py content.md

# 切换主题
python scripts/rednote_render.py content.md -t neo-brutalism

# academic 主题：技术图仍输出小红书封面和正文卡片，示例已启用 KaTeX
python scripts/rednote_render.py demos/academic.md -t academic -o output/geometry

# academic 主题的对应对比图
python scripts/rednote_render.py demos/academic-comparison.md -t academic -o output/comparison

# 交付 PNG，同时保留 HTML 制作源文件
python scripts/rednote_render.py demos/academic.md --save-html -o output/geometry

# 自定义尺寸和输出目录
python scripts/rednote_render.py content.md -t retro -o ./output
```

默认输出 `cover.png`（有封面标题时）和 `card_N.png`。所有主题共用固定画幅检查；内容过高时重排，不自动输出超长图。`--save-html` 同时在 `html/` 保存制作源文件和必要资源；仅用 `--format html` 检查中间源文件，不算完成配图。渲染脚本不调用 ImageGen。不同请求使用独立目录，不自动清理旧文件。

技术图示例：

| 示例 | 解释目标 | PNG |
|---|---|---|
| [向量几何](demos/academic.md) | 用直角三角形解释切向更新为何增加范数 | [查看卡片](demos/academic/card_1.png) |
| [对应对比](demos/academic-comparison.md) | 对比直接更新与归一化，区分临时端点和最终状态 | [查看卡片](demos/academic-comparison/card_1.png) |

两例依据欧氏向量加法、勾股定理与径向归一化构造，作为 `academic` 主题的卡片示例，不代表论文实验。假设非零权重、非零切向步长；向量角度、比例与投影关系保持真实。公式说明留在正文，图中只保留必要关系。

**参数说明**：

| 参数 | 简写 | 说明 | 默认值 |
|---|---|---|---|
| `--output-dir` | `-o` | 输出目录 | 当前目录 |
| `--theme` | `-t` | 排版主题，其他主题显式指定 | `academic` |
| `--width` | `-w` | 图片宽度（CSS px） | `1080` |
| `--height` | | 图片高度（CSS px） | `1440` |
| `--dpr` | | 设备像素比 | `2` |
| `--math` | | 数学公式渲染：`off` 或 `katex` | 读取 `front matter.math` |
| `--save-html` | | PNG 之外保留 HTML 制作源文件 | 关闭 |

---

## 项目结构

```
RedNote-Render-Skill/
├── AGENTS.md                   # 后续会话的博客目录约定
├── blogs/                      # 拖入博客：分类/博客名/正文与附件
├── output/
│   ├── <短名>/                 # 成品：图片、标题.txt、配文.txt、预览.html
│   ├── _work/                  # 独立工作目录、版本和检查记录
│   └── _archive/               # 整理前的产物与检查材料
├── SKILL.md                    # 技能定义
├── README.md
├── requirements.txt            # Python 依赖
├── requirements.lock.txt       # 已验证的完整依赖版本
├── references/
│   ├── workspace.md            # 博客投放、输出路由、版本和日常 prompt
│   ├── params.md               # 完整参数参考
│   ├── html-mode.md            # 分页 HTML 与 SVG 工作流
│   ├── content-plan.md         # 两种模式共用的图文组织与选点
│   ├── image-mode.md           # 内容图片、辅助解释图和一图流
│   ├── environment.md          # 大陆镜像安装与验证
│   └── third-party.md          # 资源来源和许可
├── assets/
│   ├── cover.html              # 封面参考模板
│   ├── card.html               # 卡片参考模板
│   ├── styles.css              # 参考模板公共样式
│   ├── example.md              # 示例 Markdown
│   ├── themes/                 # 各主题 CSS 文件
│   │   ├── default.css
│   │   ├── playful-geometric.css
│   │   ├── neo-brutalism.css
│   │   ├── botanical.css
│   │   ├── professional.css
│   │   ├── retro.css
│   │   ├── terminal.css
│   │   ├── sketch.css
│   │   ├── minimalist.css
│   │   └── academic.css
│   └── vendor/
│       └── katex/              # KaTeX 0.16.11 本地运行资源与许可
├── tests/
│   └── test_renderer.py           # 解析、分页块和 HTML 生成回归测试
├── skills/
│   └── rednote-render-skill/
│       └── SKILL.md               # 插件入口，引用根目录规范
└── scripts/
    ├── prepare_blog.py        # 准备短路径交付入口、原稿快照和工作副本
    ├── publish_blog.py        # 汇总图片、标题与配文并保留旧交付
    └── rednote_render.py       # 渲染脚本
```

---

## 注意事项

- 默认画布为 1080×1440 CSS px（本地沿用的小红书 3:4 比例）；PNG 物理像素乘以 `dpr`
- 固定画幅放不下时重新分组并增页，不缩字、裁内容或用超长图交付
- 生成后仍需查看实际图片，检查几何关系、文字重叠和遮挡；自动检查不能判断图意是否准确
- 字体使用系统已安装版本；默认 HTML＋SVG 渲染的 PNG 优先 `Microsoft YaHei`；生图指定宋体／serif 并检查实际结果
- KaTeX 资源随项目提供，公式渲染不依赖运行时网络
- SVG `<text>` 用于自然语言，LaTeX 标签放在 `.figure-label` HTML 层；具体写法见两份示例
- Windows 管道输出若遇到 `UnicodeEncodeError`，使用 `python -X utf8` 运行上述命令
- 图片可反复渲染覆盖

---

## License

MIT License © 2026 Bakameow

Original work by ZhangJia (comeonzhj).

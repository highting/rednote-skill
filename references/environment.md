# 环境安装与验证

本项目已在 Windows x64、Python 3.13.14 上运行真实浏览器测试。`requirements.lock.txt` 记录本次验证的 Python 包版本；浏览器版本由 Playwright 管理。通用包安装到当前用户环境，浏览器使用共享缓存，均不放入仓库。

## Python 包

在项目根目录执行，优先使用中国大陆镜像：

```powershell
python -m pip install --user -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements.lock.txt
python -m pip check
```

腾讯镜像已在本机完成安装。若它临时不可用，可将 `-i` 换为 `https://pypi.tuna.tsinghua.edu.cn/simple` 或 `https://mirrors.aliyun.com/pypi/simple`；大陆镜像缺包或持续失败时，再使用 `https://pypi.org/simple`。使用单次命令的 `-i`，不修改其他项目的全局源配置。

`--user` 面向系统 Python 的用户包目录；已有虚拟环境时省略它。使用 `python -m pip` 与 `python -m playwright`，避免 Windows 用户脚本目录不在 PATH 时找不到命令。

## 无头浏览器

PNG 渲染只需要 Chromium Headless Shell。PowerShell 下先试 npmmirror：

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST = 'https://npmmirror.com/mirrors/playwright'
$env:PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT = '120000'
python -m playwright install chromium-headless-shell
```

若下载实际持续超时，先等安装器退出。然后在新开的 PowerShell 窗口执行官方回退命令，使前面的进程级镜像设置不再生效：

```powershell
python -m playwright install chromium-headless-shell
```

本机曾遇到 npmmirror 文件 HEAD 可达但下载超时，最终从官方源完成 Headless Shell、FFmpeg 和 Winldd 的安装。Windows 默认缓存位于 `%LOCALAPPDATA%\ms-playwright`，无需加入仓库。升级 Playwright 后应重新执行浏览器安装命令。

如果中断安装后出现 `__dirlock`，先查看进程的命令行和父子关系。只有确认本次安装的残留进程已退出，才可删除确切的锁目录；不要在另一安装器仍运行时清锁或并发重装。

## 字体与公式

普通主题使用 **MiSans 字体**，从[小米官方下载页](https://hyperos.mi.com/font/zh/download/)获取，解压后安装 `MiSans/ttf` 中需要的字重。在 Windows 中选择“安装”可安装到当前用户；重新启动渲染进程即可使用。字体应按下载页的许可使用，本仓库不分发 MiSans 字体文件。

本机已安装官方包的十个静态字重；普通主题曾通过 Chromium `CSS.getPlatformFontsForNode` 验证正文使用 `MiSans`、代码使用 `Consolas`。`academic` 的 HTML 导出会将中文覆盖为 `Microsoft YaHei`；基础主题中的宋体栈不代表最终生效字体。生图辅助图可按其既有 prompt 使用宋体／serif。字体是否生效应检查实际渲染，不因参考截图使用某种字体就改变当前设置。

KaTeX 0.16.11 的 JS、CSS、字体已内置在 `assets/vendor/katex`。无需 Node.js 或 npm 即可渲染公式；资源来源及许可见 [third-party.md](third-party.md)。

新四场景的源码模板使用可嵌入的Noto Sans SC作为离线中文回退。字体包不纳入Git；首次构建或运行模板测试前显式执行 `python -X utf8 scripts/download_content_fonts.py`，它下载固定版本并核对SHA-256。缓存受Git忽略，之后构建和成品阅读不再请求字体服务器。已有允许嵌入的字体可通过构建器 `--font` 使用；复用本地Fontsource包的方法见[字体说明](../assets/vendor/noto-sans-sc/README.md)。

## 验证与示例

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/rednote_render.py demos/academic.md -t academic -o output/geometry
python -X utf8 scripts/rednote_render.py demos/academic-comparison.md -t academic -o output/comparison
```

测试包含真实浏览器输出、离线公式、根号可见性、画布越界、非法公式及分页内容保留；缺少依赖或浏览器会失败，应先完成安装。PNG 仍需目视核对几何、标签位置和遮挡。

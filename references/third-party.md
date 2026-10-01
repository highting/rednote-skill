# 第三方资源

## KaTeX

- 版本：0.16.11。
- 上游：[KaTeX](https://katex.org/)，npm 包 `katex@0.16.11`。
- 获取地址：`https://registry.npmmirror.com/katex/-/katex-0.16.11.tgz`。
- 上游包完整性：`sha512-RQrI8rlHY92OLf3rho/Ts8i/XvjgguEjOkO1BEXcU3N8BqPpSzBNwV/G0Ukr+P/l3ivvJUE/Fa/CwbS6HesGNQ==`。
- 仓库仅保留发行包的 `katex.min.js`、`katex.min.css`、`contrib/auto-render.min.js`、字体和原始 MIT 许可；位置为 `assets/vendor/katex`。
- 版权及完整许可见 [LICENSE](../assets/vendor/katex/LICENSE)。

## MiSans

普通主题使用 MiSans 字体。[官方来源与许可](https://hyperos.mi.com/font/zh/download/)。字体安装在操作系统用户环境，不随本仓库分发；代码和公式分别使用等宽字体与 KaTeX 数学字体。

## Noto Sans SC

- 上游：[Google Noto CJK](https://github.com/notofonts/noto-cjk)，通过 `@fontsource/noto-sans-sc@5.3.0` 的400字重WOFF2子集分发。
- 许可：SIL Open Font License 1.1，见 [LICENSE](../assets/vendor/noto-sans-sc/LICENSE)。
- 仓库保存来源、Unicode范围、大小和SHA-256清单，不提交字体文件或base64字体包。运行 `scripts/download_content_fonts.py` 从固定版本镜像下载到受Git忽略的本地缓存，也可复用已有Fontsource包。
- 构建器只内嵌当前HTML需要的子集；离线成品保留原始字体许可。

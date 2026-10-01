# Noto Sans SC 离线中文字体

来源：Fontsource 的 `@fontsource/noto-sans-sc` 5.3.0（Google Noto Sans SC），SIL Open Font License 1.1，许可见 LICENSE。仓库只保存许可与 `font-manifest.json` 下载/校验清单，不提交字体包。首次使用源码模板前运行：

```bash
python -X utf8 scripts/download_content_fonts.py
```

脚本从固定版本的 jsDelivr npm 镜像下载400字重的101个 WOFF2 Unicode 子集（约2.4MB原始字体），逐个核对SHA-256后原子写入 `font-bundle.json`。缓存受Git忽略；再次运行会校验并复用完整缓存，下载失败不会覆盖现有缓存。网络只发生在显式执行下载命令时，构建及成品阅读不访问字体服务器。粗体由浏览器合成。

已下载Fontsource包时可离线建立缓存：

```bash
python -X utf8 scripts/download_content_fonts.py --source-dir /path/to/node_modules/@fontsource/noto-sans-sc
```

也可使用构建器的 `--font /path/to/licensed-font.woff2`，无需下载默认缓存。使用字体前确认其许可允许嵌入。

保留MiSans等系统中文字体优先级，提供离线Noto回退；单次`--font`可覆盖默认资源。字体资源不会自动修复图标签太小、布局遮挡或罕见缺字，仍需实际查看成品。

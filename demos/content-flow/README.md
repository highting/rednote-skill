# 同题制作素材：在线 Softmax

`main.md` 是本轮四场景试作共用的教学材料，包含条件、符号、可核对的算例和实际原论文链接，不是性能实验。演示如何从相同事实底稿分别组织学习、博客、汇报与手机图文。

将本目录主稿复制到 `inputs/示例/在线Softmax/main.md`，再准备所需场景：

```bash
python -X utf8 scripts/prepare_content.py "inputs/示例/在线Softmax" --scene learning --name Softmax学习
python -X utf8 scripts/prepare_content.py "inputs/示例/在线Softmax" --scene blog --name Softmax博客
python -X utf8 scripts/prepare_content.py "inputs/示例/在线Softmax" --scene report --name Softmax汇报
python -X utf8 scripts/prepare_content.py "inputs/示例/在线Softmax" --scene rednote --name Softmax图文
```

AI读取生成的 `work/任务Prompt.txt` 与材料，按选定场景完成内容。可用 `build_content_template.py` 组装已写好的HTML片段；模板默认的两页示例只是结构起点，不能当成Softmax成品。随后执行准备结果中的renderer_command，实际查看HTML与图像，记录评审，再完成本地短路径交付。

本轮原版学习文包含3幅核心图；修正版5幅，博客6幅，汇报8页/10分钟，小红书6页。图数只描述本次不同解释职责，不是未来每题必须达到的数量。四个完整成品实际接入新renderer，学习/博客各交首屏预览，汇报8张1280×720与图文6张1080×1440；离线资源、运行与边界检查均通过。素材与字体适配后仍应逐题评审，不能依据这个示例断言所有主题稳定通过。

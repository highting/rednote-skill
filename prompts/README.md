# 场景 Prompt v2

直接复制 [`standalone/learning.txt`](standalone/learning.txt)、[`blog.txt`](standalone/blog.txt)、[`report.txt`](standalone/report.txt) 或 [`rednote.txt`](standalone/rednote.txt)，填写末尾任务输入。仅制作图用 [`diagram.txt`](standalone/diagram.txt)。

维护时只编辑 `common.txt` 和 `scenes/<scene>.txt`，运行 `python scripts/export_prompts.py` 更新独立版本。`prepare_content.py` 读取公共源和选定场景，加入本次素材路径及范围，生成工作目录里的 `任务Prompt.txt`。

四种场景决定内容策划与交付；`html` / `images` 决定辅助图工具。机制图覆盖由卡点选点表检查，4–7幅等范围是软预算，不能凑图或替代内容判断。暖石白、墨青、灰紫是可覆盖的默认方案，不是所有题材的硬限制。

这版约束依据同一模型配置的独立代理、在线 Softmax 同主题原版／改版学习文以及博客、汇报、小红书样例修正。学习图解由3幅增加到5幅；修正了数值图比例、页脚侵入、中文混排回退与交互绑定。单题单轮评审不能保证所有主题都符合主观审美；本题不需要AI生图，未测生图稳定性。

仓库交付协议补充离线资源、显式分页、激活hook与真实检查结果，内容策略与测试版一致。脚本不自动调用AI，也不代替技术和视觉评审。

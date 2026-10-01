# 固定测试任务
主题：在线 Softmax：最大值变大时，旧状态为什么要缩放。
受众：做 LLM 训练工程、熟悉矩阵运算，但首次系统理解分块 Softmax 的中文读者。
范围：稳定 Softmax、分块三状态 m/l/U、旧状态重缩放、算例、tile shape、实现口径与边界。不要讲完全部 FlashAttention，也不使用性能数字。未指定字数、图数或目录设计。

# 已核对的来源与口径
1. Milakov & Gimelshein, Online normalizer calculation for softmax (2018), https://arxiv.org/pdf/1805.02867 ，第3节 Algorithm 3：运行最大值变化后，先按 exp(m_old-m_new) 缩放旧归一化分母，再加新项。
2. Dao et al., FlashAttention (2022), https://arxiv.org/html/2205.14135v2 ，第3.1节、Algorithm 1、附录B：分块避免在 HBM 物化完整 N×N 注意力矩阵；原版 Algorithm 1 的 O 是每次归一化的中间输出。本文为教学采用未归一化累加器 U，不冒称论文原符号。
3. Dao, FlashAttention-2 (2023), https://arxiv.org/pdf/2307.08691 ，第3.1节、Algorithm 1：可以延迟到循环结束再对输出累加器归一化。

# 自行推导的统一教学模型（不是内核源码）
固定一个 query row，已见分数集合 A，m=max s，l=sum exp(s-m)，U=sum exp(s-m)*v。新块B：m'=max(m,max B)，alpha=exp(m-m')，p_B=exp(s_B-m')；l'=alpha*l+sum p_B，U'=alpha*U+p_B V_B，最终 O=U/l。alpha 不大于1；旧最大值不变则 alpha=1。l 与 U 同尺度。不要混用归一化 O 的递推式。
首次块 m=-inf,l=0,U=0；只在存在有限有效分数时递推有效。全masked行需实现单独处理，不能直接写 -inf-(-inf)。说明数学等价与浮点舍入不同。
Q tile (Bq,d), K/V tile (Bk,d), S/P tile (Bq,Bk), m/l (Bq), U/O (Bq,d)。展示 Bq=2,Bk=3,d=4 的教学形状，但核心数值算例先沿一个row，不把矩阵总览当中间矩阵实际物化。

# 固定贯穿算例（教学构造，不是实验）
旧块 scores=[1,2], V=[10,20]，新块 scores=[3], V=[30]。m_old=2，l_old=exp(-1)+1，U_old=10exp(-1)+20。m_new=3，alpha=exp(-1)，新块 p=1。l_new=alpha*l_old+1，U_new=alpha*U_old+30，O=U_new/l_new。如果不重缩放旧l/U，旧块被高估。逐步计算时保留足够精度。

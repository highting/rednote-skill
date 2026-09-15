---
title: "直接更新与归一化"
math: katex
---

<div class="figure-scene">
<svg viewBox="0 0 1440 720" role="img" aria-label="相同切向更新的对比：直接更新增加范数，径向归一化将临时端点投影回原范数等长弧">
  <defs>
    <marker id="weight-arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0 0 L12 6 L0 12 Z" fill="#3568B0" />
    </marker>
    <marker id="step-arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0 0 L12 6 L0 12 Z" fill="#827C72" />
    </marker>
    <marker id="projection-arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0 0 L12 6 L0 12 Z" fill="#B85C2E" />
    </marker>
  </defs>
  <text class="figure-title" x="40" y="65">保留切向步长，或投影回原范数</text>
  <text class="figure-note" x="40" y="120">相同起点 · 相同切向更新</text>
  <text class="figure-heading" x="170" y="210">直接更新</text>
  <text class="figure-heading" x="890" y="210">归一化回原范数</text>
  <path d="M514.68 570.78 A350 350 0 0 0 370.75 223.30" class="vector-reference" fill="none" />
  <path d="M1234.68 570.78 A350 350 0 0 0 1090.75 223.30" class="vector-reference" fill="none" />
  <line x1="170" y1="510" x2="520" y2="510" class="vector-primary" marker-end="url(#weight-arrow)" />
  <line x1="520" y1="510" x2="520" y2="270" class="vector-update" marker-end="url(#step-arrow)" />
  <line x1="170" y1="510" x2="520" y2="270" class="vector-primary" marker-end="url(#weight-arrow)" />
  <path d="M494 510 L494 484 L520 484" class="geometry-mark" />
  <circle cx="170" cy="510" r="5" fill="#2F2D29" />
  <line x1="890" y1="510" x2="1240" y2="510" class="vector-primary" marker-end="url(#weight-arrow)" />
  <line x1="1240" y1="510" x2="1240" y2="270" class="vector-update" marker-end="url(#step-arrow)" />
  <line x1="890" y1="510" x2="1240" y2="270" class="vector-reference" />
  <line x1="890" y1="510" x2="1178.6551" y2="312.0651" class="vector-primary" marker-end="url(#weight-arrow)" />
  <line x1="1240" y1="270" x2="1178.6551" y2="312.0651" class="vector-contrast" marker-end="url(#projection-arrow)" />
  <path d="M1214 510 L1214 484 L1240 484" class="geometry-mark" />
  <circle cx="890" cy="510" r="5" fill="#2F2D29" />
  <circle cx="1240" cy="270" r="6" fill="#FAF9F5" stroke="#6B675F" stroke-width="2" />
</svg>
<div class="figure-label primary" style="left:23%;top:77%">\(W_t\)</div>
<div class="figure-label primary" style="left:73%;top:77%">\(W_t\)</div>
<div class="figure-label primary" style="left:21%;top:51%">\(W_{t+1}\)</div>
<div class="figure-label primary" style="left:71%;top:51%">\(\hat W_{t+1}\)</div>
<div class="figure-label updated" style="left:40.5%;top:56%">\(-\eta u_t\)</div>
<div class="figure-label updated" style="left:90.5%;top:56%">\(-\eta u_t\)</div>
<div class="figure-label note" style="left:91%;top:36%">\(\widetilde W_{t+1}\)</div>
<div class="figure-label" style="left:25%;top:92%">\(\|W_{t+1}\|>\|W_t\|\)</div>
<div class="figure-label" style="left:75%;top:92%">\(\|\hat W_{t+1}\|=\|W_t\|\)</div>
</div>

---
title: "切向更新为何增加权重范数"
math: katex
---

<div class="figure-scene">
<svg viewBox="0 0 1440 720" role="img" aria-label="直角三角形：旧权重与切向步长是直角边，新权重是更长的斜边">
  <defs>
    <marker id="weight-arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0 0 L12 6 L0 12 Z" fill="#3568B0" />
    </marker>
    <marker id="step-arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0 0 L12 6 L0 12 Z" fill="#827C72" />
    </marker>
  </defs>
  <text class="figure-title" x="40" y="65">切向更新为何增加权重范数</text>
  <text class="figure-note" x="315" y="185">原范数等长弧</text>
  <path d="M160 570 L640 570 L640 210 Z" fill="#E9EEF3" />
  <path d="M632.71 653.35 A480 480 0 0 0 468.54 202.30" class="vector-reference" fill="none" />
  <line x1="160" y1="570" x2="640" y2="570" class="vector-primary" marker-end="url(#weight-arrow)" />
  <line x1="640" y1="570" x2="640" y2="210" class="vector-update" marker-end="url(#step-arrow)" />
  <line x1="160" y1="570" x2="640" y2="210" class="vector-primary" marker-end="url(#weight-arrow)" />
  <path d="M612 570 L612 542 L640 542" class="geometry-mark" />
  <circle cx="160" cy="570" r="5" fill="#2F2D29" />
  <text class="figure-note" x="125" y="615">原点</text>
  <text class="figure-note" x="675" y="605">更新前</text>
  <text class="figure-note" x="670" y="200">更新后</text>
  <text class="figure-heading" x="930" y="290">沿切线移动</text>
  <text x="930" y="350">端点移出等长弧</text>
</svg>
<div class="figure-label primary" style="left:27%;top:86%">\(W_t\)</div>
<div class="figure-label primary" style="left:26%;top:48%">\(W_{t+1}\)</div>
<div class="figure-label updated" style="left:50%;top:54%">\(-\eta u_t\)</div>
<div class="figure-label" style="left:77%;top:60%">\(\|W_{t+1}\|>\|W_t\|\)</div>
<div class="figure-label note" style="left:77%;top:80%">\(u_t\perp W_t,\quad \eta\|u_t\|>0\)</div>
</div>

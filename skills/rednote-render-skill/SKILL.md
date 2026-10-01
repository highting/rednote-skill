---
name: rednote-render-skill
description: Create learning documents, technical blogs, presentation reports, and RedNote image posts. Plan the selected scene, produce portable offline HTML, and validate or export PNG pages with supporting visuals.
---

# Content Creation and HTML → PNG

Follow the canonical workflow in [`../../SKILL.md`](../../SKILL.md). Resolve paths relative to the repository/plugin root, two directories above this entry.

Choose `learning`, `blog`, `report`, or `rednote` from the reader and intended use. `diagram` is a narrow entry for explicitly requested figures. Then choose the supporting-visual mode: `html` or `images`. The mode does not determine the article structure or delivery format; precise values, shapes, formulas, algorithm states, and geometry still use verifiable programmatic figures.

Read [`../../references/content-workflow.md`](../../references/content-workflow.md) and the chosen scene in [`../../references/content-scenes.md`](../../references/content-scenes.md). Prepare a work copy with `prepare_content.py`, combine `prompts/common.txt` and `prompts/scenes/<scene>.txt`, create a complete self-contained `index.html`, and use `render_content.py` for desktop checks and the scene's exports. `learning` and `blog` default to HTML; image export is explicit. `report` and `rednote` export fixed-page PNGs. Inspect actual output before marking the run completed and publishing with `publish_content.py`.

The shared scripts do not author content, invoke image-generation APIs, or publish to social platforms. Preserve original inputs. Copyable complete prompts are in `prompts/standalone/`; maintain the common/scene sources and rerun `python scripts/export_prompts.py` rather than editing derived copies. Keep the legacy Markdown/academic commands for explicit compatibility use, without letting their old colors or 3:4 rules override the new scene defaults. This repository entry is source code; it does not claim installation into a personal skill directory.

"""A review page for one transcription file (QB-10): each printed question image next to
the transcribed text, with the LaTeX rendered.

    python -m scibowl_qb.parse --set set01            # writes output/questions.json and output/images
    python -m scibowl_qb.transcription_review transcriptions/ms/set01.yaml

The page is one self-contained HTML file: images, and KaTeX's script, styles and fonts, are
embedded (QB-34), so it renders the same in any viewer, offline too. Mark entries `reviewed: true` in the YAML file once they match the image.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

from . import transcriptions as tr

# KaTeX 0.16.47 (MIT, see vendor/katex/LICENSE), the version the website uses. Only the woff2
# fonts are kept: every current browser reads them.
KATEX_DIR = Path(__file__).parent / "vendor" / "katex"
_FONT_SRC = re.compile(r'src:url\(fonts/([\w-]+\.woff2)\) format\("woff2"\)[^;}]*')


def katex_css() -> str:
    """katex.min.css with each font embedded as a data: URL instead of a fonts/ link."""
    def embed(m: re.Match) -> str:
        data = base64.b64encode((KATEX_DIR / "fonts" / m.group(1)).read_bytes()).decode()
        return f'src:url(data:font/woff2;base64,{data}) format("woff2")'
    css, n = _FONT_SRC.subn(embed, (KATEX_DIR / "katex.min.css").read_text(encoding="utf-8"))
    if n == 0 or "url(fonts/" in css:
        raise RuntimeError("katex.min.css has a font rule this code does not embed")
    return css


def katex_js() -> str:
    js = (KATEX_DIR / "katex.min.js").read_text(encoding="utf-8")
    if "</script" in js.lower():
        raise RuntimeError("katex.min.js can't be inlined as is")
    return js


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{katex_css}</style>
<script>{katex_js}</script>
<script>
// Same rules as the website (lib/math.ts): $...$ is math in display style, \$ is a dollar sign,
// and \textbf{{...}} outside math is bold text.
function renderAll() {{
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const text = (s) => esc(s.replace(/\\\$/g, "$")).replace(/\\textbf\{{([^{{}}]*)\}}/g, "<strong>$1</strong>");
  for (const el of document.querySelectorAll(".latex")) {{
    const parts = el.textContent.split(/(?<!\\)\$/);
    if (parts.length % 2 === 0) {{ el.classList.add("bad"); continue; }}
    try {{
      el.innerHTML = parts.map((p, i) => i % 2 === 0 ? text(p)
        : katex.renderToString("\\displaystyle " + p, {{ throwOnError: true, output: "html", strict: "ignore" }})).join("");
    }} catch (e) {{ el.classList.add("bad"); el.title = String(e); }}
  }}
}}
document.addEventListener("DOMContentLoaded", renderAll);
</script>
<style>
  body {{ font: 16px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 1200px; padding: 16px; color: #111; background: #fff; }}
  h1 {{ font-size: 1.4rem; }}
  .q {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; border-top: 1px solid #ddd; padding: 16px 0; }}
  .q img {{ max-width: 100%; border: 1px solid #eee; }}
  .id {{ font: 13px ui-monospace, monospace; color: #555; }}
  .label {{ font-size: 13px; color: #555; margin-top: 8px; }}
  .latex {{ font-size: 1.1rem; }}
  .plain {{ font: 13px ui-monospace, monospace; color: #444; white-space: pre-wrap; }}
  .status {{ font-size: 13px; font-weight: 600; }}
  .bad {{ outline: 2px solid #c00; }}
  .todo {{ color: #a15c00; }} .done {{ color: #116329; }}
  @media (max-width: 700px) {{ .q {{ grid-template-columns: 1fr; }} }}
</style></head><body>
<h1>{title}</h1>
<p>{intro}</p>
{body}
</body></html>
"""


def _img(path: Path) -> str:
    if not path.exists():
        return f'<p class="todo">Image not found: {html.escape(str(path))}</p>'
    data = base64.b64encode(path.read_bytes()).decode()
    return f'<img alt="" src="data:image/png;base64,{data}">'


def _field(label: str, f: dict) -> str:
    return (f'<div class="label">{label}</div><div class="latex">{html.escape(f["latex"])}</div>'
            f'<div class="plain">{html.escape(f["text"])}</div>')


def render(path: Path, data_file: Path, todo_only: bool = False) -> str:
    """data_file: a questions.json with its images/ folder next to it (parse output or an unzipped release)."""
    entries = tr.load_file(path)
    reviewed = sum(t.reviewed for t in entries)
    if todo_only:
        entries = [t for t in entries if not t.reviewed]
    images = {q["id"]: q["images"].get("entire") for q in json.loads(data_file.read_text(encoding="utf-8"))["questions"]}
    parts = []
    for t in entries:
        right = [f'<div class="id">{html.escape(t.id)}</div>',
                 f'<div class="status {"done" if t.reviewed else "todo"}">{"Reviewed" if t.reviewed else "Not reviewed yet"}</div>',
                 _field("Question", t.question)]
        for letter, c in (t.choices or {}).items():
            right.append(_field(f"Choice {letter}", c))
        right.append(_field(f"Answer: choice {t.answer['choice']}" if t.choices else "Answer", t.answer))
        for key, label in (("accept", "Accept"), ("do_not_accept", "Do not accept")):
            for alt in t.answer.get(key, []):
                right.append(_field(label, alt))
        parts.append(f'<section class="q"><div>{_img(data_file.parent / images[t.id]) if images.get(t.id) else '<p class="todo">No image for this ID in the data</p>'}</div><div>{"".join(right)}</div></section>')
    title = f"Transcription review: {path.parent.name}/{path.stem}"
    shown = f"Showing the {len(entries)} not reviewed yet. " if todo_only else ""
    intro = (f"{shown}{reviewed} of {len(tr.load_file(path))} questions reviewed. Left: the printed question. Right: the transcription, "
             "rendered, with the plain text below it. Check the rendered version against the printed question, including any ACCEPT answers. "
             f"Approved entries get <code>reviewed: true</code> in <code>{html.escape(path.as_posix())}</code>.")
    return PAGE.format(title=html.escape(title), intro=intro, body="\n".join(parts), katex_css=katex_css(), katex_js=katex_js())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", type=Path, help="e.g. transcriptions/ms/set01.yaml")
    ap.add_argument("--data", type=Path, default=Path("output/questions.json"),
                    help="questions.json from a parse with images (or an unzipped release), with images/ next to it")
    ap.add_argument("--todo", action="store_true", help="only the entries not reviewed yet")
    ap.add_argument("--out", type=Path, help="default: output/review-<level>-<set>.html")
    args = ap.parse_args(argv)
    out = args.out or Path("output") / f"review-{args.file.parent.name}-{args.file.stem}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(args.file, args.data, args.todo), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

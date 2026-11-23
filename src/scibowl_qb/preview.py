"""A simple HTML page for eyeballing parsed questions next to their PDF images.

    python -m scibowl_qb.preview output/questions.json output/preview.html

Image paths in the page are relative (images/...), so put the page next to the
images folder. Flagged questions are highlighted, and a checkbox hides the rest.
"""

from __future__ import annotations

import html
import json
import sys
from collections import defaultdict
from pathlib import Path

STYLE = """
body{font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:16px;color:#1d1d1f;background:#fff}
h1{font-size:22px}h2{font-size:18px;margin-top:32px;border-bottom:1px solid #ccc}
.q{display:grid;grid-template-columns:1fr 1fr;gap:16px;border:1px solid #ddd;border-radius:6px;padding:12px;margin:12px 0}
.q.flag{border-color:#d33;background:#fff5f5}.meta{font-size:12px;color:#555}.ans{font-weight:600}
.notes{font-size:12px;color:#b00}img{max-width:100%;border:1px solid #eee}
@media (max-width:700px){.q{grid-template-columns:1fr}}
body.only-flagged .q:not(.flag){display:none}
"""


def _e(text) -> str:
    return html.escape(str(text)) if text is not None else ""


def render(data: dict, title: str = "Question preview") -> str:
    questions = data["questions"]
    flagged = sum("needs_review" in q["quality"]["flags"] for q in questions)
    rounds: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        rounds[f"{q['source']['level']}/{q['source']['set']}/{q['source']['round']}"].append(q)

    out = [f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{_e(title)}</title><style>{STYLE}</style><body>",
           f"<h1>{_e(title)}</h1><p>{len(questions)} questions in {len(rounds)} rounds, {flagged} flagged needs_review. "
           "Left: parsed text. Right: the PDF image.</p>",
           "<label><input type='checkbox' onchange=\"document.body.classList.toggle('only-flagged',this.checked)\"> "
           "Show only flagged questions</label>"]
    for name, qs in rounds.items():
        out.append(f"<h2>{_e(name)}</h2>")
        for q in qs:
            is_flagged = "needs_review" in q["quality"]["flags"]
            choices = ""
            if q["choices"]:
                choices = "<br>".join(f"{k}) {_e(v['text'])}" for k, v in q["choices"].items())
            ans = q["answer"]
            answer = (f"{ans['choice']}) " if ans.get("choice") else "") + _e(ans["text"])
            for key, label in (("accept", "accept"), ("do_not_accept", "do not accept")):
                if ans.get(key):
                    answer += f" <span class='meta'>({label}: {_e('; '.join(ans[key]))})</span>"
            image = q["images"].get("entire")
            img = f"<img loading='lazy' src='{_e(image)}' alt=''>" if image else "<p class='meta'>(no image)</p>"
            notes = "<br>".join(_e(n) for n in q["quality"]["notes"])
            out.append(
                f"<div class='q{' flag' if is_flagged else ''}' id='{_e(q['id'])}'><div>"
                f"<div class='meta'>{_e(q['id'])} · {_e(q['category'])} ({_e(q['category_raw'])}) · {_e(q['format'])}</div>"
                f"<p>{_e(q['question']['text'])}</p><p>{choices}</p><p class='ans'>ANSWER: {answer}</p>"
                f"<div class='notes'>{notes}</div></div><div>{img}</div></div>"
            )
    out.append("</body>")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    Path(args[1]).write_text(render(data), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""A self-contained page for checking one set's topic tags (QB-12).

Usage:
    python -m scibowl_qb.parse --level ms --set set15 --no-images
    python -m scibowl_qb.tag_review --set set15

Reads output/questions.json and writes output/tag-review-<level>-<set>.html: counts per
discipline and topic, how the printed subjects map to disciplines, and every question with
its answer and tags, grouped by topic. Filters pick a discipline or a printed subject.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import REPO_ROOT
from . import tags as tg

CATEGORY_LABELS = {
    "life_science": "Life Science", "physical_science": "Physical Science", "earth_and_space": "Earth and Space",
    "energy": "Energy", "math": "Math", "general_science": "General Science", "biology": "Biology",
    "chemistry": "Chemistry", "physics": "Physics",
}

CSS = """
:root { --bg:#fbfaf7; --fg:#1d1d1f; --muted:#6b6b70; --line:#e3e1db; --card:#ffffff; --accent:#2f6f5e;
        --chip:#eef3f1; --chip-fg:#24574a; --warn:#fff4dc; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#161617; --fg:#ececec; --muted:#a0a0a6; --line:#2e2e31; --card:#1f1f21; --accent:#7cc2ad;
          --chip:#233430; --chip-fg:#a6dccb; --warn:#3a3220; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:980px; margin:0 auto; padding:24px 16px 64px; }
h1 { font-size:24px; margin:0 0 4px; } h2 { font-size:18px; margin:32px 0 8px; } h3 { font-size:16px; margin:0; }
p.lead { color:var(--muted); margin:0 0 16px; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:600; }
td.n { text-align:right; font-variant-numeric:tabular-nums; }
.wrap { overflow-x:auto; }
.filters { position:sticky; top:0; background:var(--bg); padding:10px 0; border-bottom:1px solid var(--line);
           display:flex; gap:12px; flex-wrap:wrap; align-items:center; z-index:1; }
select { font:inherit; padding:4px 8px; border-radius:6px; border:1px solid var(--line); background:var(--card); color:var(--fg); }
details.topic { background:var(--card); border:1px solid var(--line); border-radius:10px; margin:10px 0; }
details.topic > summary { cursor:pointer; padding:10px 14px; display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }
details.topic > summary .count { color:var(--muted); font-size:13px; }
.q { border-top:1px solid var(--line); padding:10px 14px; }
.q .meta { color:var(--muted); font-size:12px; display:flex; gap:8px; flex-wrap:wrap; }
.q .text { margin:4px 0; }
.q .choices { margin:2px 0 4px; padding-left:4px; list-style:none; color:var(--fg); font-size:14px; }
.q .answer { font-size:14px; } .q .answer b { color:var(--accent); }
.chip { display:inline-block; background:var(--chip); color:var(--chip-fg); border-radius:999px; padding:0 8px; font-size:12px; }
.chip.other { background:var(--warn); color:var(--fg); }
.hidden { display:none !important; }
"""

JS = """
const d = document.getElementById('f-disc'), c = document.getElementById('f-cat');
function apply() {
  document.querySelectorAll('.q').forEach(q => {
    const ok = (!d.value || q.dataset.disc.split(' ').includes(d.value)) && (!c.value || q.dataset.cat === c.value);
    q.classList.toggle('hidden', !ok);
  });
  document.querySelectorAll('details.topic').forEach(t => {
    const n = t.querySelectorAll('.q:not(.hidden)').length;
    t.classList.toggle('hidden', n === 0);
    t.querySelector('.count').textContent = n + (n === 1 ? ' question' : ' questions');
  });
}
d.addEventListener('change', apply); c.addEventListener('change', apply);
"""


def _e(s) -> str:
    return html.escape(str(s or ""))


def _question_html(q: dict, topic: str) -> str:
    rnd = q["source"]["round_number"] or q["source"]["round"]
    others = [t for t in q["tags"]["topics"] if t != topic]
    chips = "".join(f'<span class="chip other">also: {_e(t)}</span>' for t in others)
    choices = ""
    if q["choices"]:
        choices = '<ul class="choices">' + "".join(f"<li>{k}) {_e(v['text'])}</li>" for k, v in q["choices"].items()) + "</ul>"
    answer = q["answer"]["text"] or q["answer"]["raw"]
    if q["answer"].get("choice"):
        answer = f"{q['answer']['choice']}) {answer}"
    return (
        f'<div class="q" data-disc="{_e(" ".join(q["tags"]["disciplines"]))}" data-cat="{_e(q["category"])}">'
        f'<div class="meta"><span>Round {_e(rnd)} {"toss-up" if q["part"] == "tossup" else "bonus"} {q["number"]}</span>'
        f'<span>printed: {_e(q["category_raw"])}</span>{chips}</div>'
        f'<div class="text">{_e(q["question"]["text"])}</div>{choices}'
        f'<div class="answer"><b>Answer:</b> {_e(answer)}</div></div>'
    )


def build(questions: list[dict], topic_list: tg.TopicList, title: str) -> str:
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        for t in q["tags"]["topics"]:
            by_topic[t].append(q)
    disc_counts = Counter(d for q in questions for d in q["tags"]["disciplines"])
    mapping = Counter((q["category"], " + ".join(topic_list.disciplines[d] for d in q["tags"]["disciplines"])) for q in questions)
    multi = sum(1 for q in questions if len(q["tags"]["topics"]) > 1)

    out = [f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           f"<title>{_e(title)}</title><style>{CSS}</style></head><body><main>",
           f"<h1>{_e(title)}</h1>",
           f"<p class=\"lead\">{len(questions)} questions, {len(by_topic)} of {len(topic_list.topics)} topics used, "
           f"{multi} questions with more than one topic. Tags are AI-made and not reviewed yet.</p>"]

    out.append("<h2>Printed subject to discipline</h2><div class=\"wrap\"><table><tr><th>Printed subject</th><th>Discipline from tags</th><th class=\"n\">Questions</th></tr>")
    for (cat, disc), n in sorted(mapping.items(), key=lambda kv: (kv[0][0], -kv[1])):
        out.append(f"<tr><td>{_e(CATEGORY_LABELS.get(cat, cat))}</td><td>{_e(disc)}</td><td class=\"n\">{n}</td></tr>")
    out.append("</table></div>")

    out.append("<h2>Topic list</h2><div class=\"wrap\"><table><tr><th>Discipline</th><th>Topic ID</th><th>Topic</th><th class=\"n\">Questions</th></tr>")
    for topic, (disc, label) in topic_list.topics.items():
        n = len(by_topic.get(topic, []))
        out.append(f"<tr><td>{_e(topic_list.disciplines[disc])}</td><td><code>{_e(topic)}</code></td><td>{_e(label)}</td>"
                   f"<td class=\"n\">{n or '&ndash;'}</td></tr>")
    out.append("</table></div>")

    disc_opts = "".join(f'<option value="{_e(d)}">{_e(label)} ({disc_counts[d]})</option>'
                        for d, label in topic_list.disciplines.items() if disc_counts[d])
    cats = Counter(q["category"] for q in questions)
    cat_opts = "".join(f'<option value="{_e(c)}">{_e(CATEGORY_LABELS.get(c, c))} ({n})</option>' for c, n in sorted(cats.items()))
    out.append("<h2>Questions by topic</h2>"
               f'<div class="filters"><label>Discipline <select id="f-disc"><option value="">All</option>{disc_opts}</select></label>'
               f'<label>Printed subject <select id="f-cat"><option value="">All</option>{cat_opts}</select></label></div>')
    for topic, (disc, label) in topic_list.topics.items():
        qs = by_topic.get(topic)
        if not qs:
            continue
        out.append(f'<details class="topic"><summary><h3>{_e(label)}</h3><span class="chip">{_e(topic_list.disciplines[disc])}</span>'
                   f'<span class="count">{len(qs)} questions</span></summary>')
        out.extend(_question_html(q, topic) for q in qs)
        out.append("</details>")
    out.append(f"<script>{JS}</script></main></body></html>")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a page for checking one set's topic tags.")
    ap.add_argument("--level", default="ms")
    ap.add_argument("--set", dest="set_name", required=True, help="e.g. set15")
    ap.add_argument("--questions", type=Path, default=REPO_ROOT / "output" / "questions.json")
    ap.add_argument("--tags", type=Path, default=tg.DEFAULT_DIR)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    topic_list = tg.load(args.tags).topic_list
    if topic_list is None:
        print(f"No topics.yaml in {args.tags}", file=sys.stderr)
        return 1
    data = json.loads(args.questions.read_text(encoding="utf-8"))
    questions = [q for q in data["questions"]
                 if q["source"]["level"] == args.level and q["source"]["set"] == args.set_name]
    untagged = [q["id"] for q in questions if not q["tags"]["topics"]]
    if not questions or untagged:
        print(f"{args.level}/{args.set_name}: {len(questions)} questions, {len(untagged)} without tags. "
              "Parse the set after adding its tags file.", file=sys.stderr)
        return 1
    out = args.out or args.questions.parent / f"tag-review-{args.level}-{args.set_name}.html"
    out.write_text(build(questions, topic_list, f"Topic tags: {args.level.upper()} {args.set_name}"), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Topic tags (QB-11, QB-12)

- `topics.yaml` is the topic list: the six disciplines used from 2022 (biology, chemistry, physics, earth and space, energy, math) and the topics under each. It is a first draft for John to edit.
- `<level>/<set>.yaml` tags every question in one set with one or more topic IDs. A question's `tags.disciplines` come from its topics, so an older Life Science question tagged `genetics` is filed under biology.

```yaml
source: Who or what made these, and when
tagged_by: ai          # or human
reviewed: false        # true once John has checked the set
questions:
  ms-set15-set-1-ms-2021-q01-tossup: [atoms]
  ms-set15-set-1-ms-2021-q04-bonus: [cells, genetics]
```

- The parser applies tags last. A tags file must cover every question in its set; an unknown topic, a missing question or an ID that matches nothing stops the parse.
- The DOE-lab "Energy" questions in older sets are tagged by what they ask about (a question about lichens is `ecology`, so biology). The `energy` discipline is for questions about energy itself: batteries, fuels, nuclear power, renewables. The printed subject stays in `category`.
- Renaming a topic's label is safe. Changing a topic ID means changing every tags file that uses it.

## Review

```bash
python -m scibowl_qb.parse --level ms --set set15 --no-images
python -m scibowl_qb.tag_review --set set15
```

This writes `output/tag-review-ms-set15.html`: how printed subjects map to disciplines, counts per topic, and every question with its answer, grouped by topic, with filters by discipline and printed subject. To fix a tag, edit the set's file. When the set is right, set `reviewed: true`.

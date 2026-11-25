# Topic tags (QB-11, QB-12)

- `topics.yaml` is the topic list: the six disciplines used from 2022 (biology, chemistry, physics, earth and space, energy, math) and the topics under each. It is a first draft for John to edit.
- `<level>/<set>.yaml` tags every question in one set with one or more topic IDs. A question's `tags.disciplines` come from its topics, so an older Life Science question tagged `genetics` is filed under biology.
- Each discipline has a `-misc` topic (`biology-misc`, `energy-misc`, ...) for questions that fit none of its topics well.

```yaml
source: Who or what made these, and when
tagged_by: ai          # or human
reviewed: false        # true once John has checked the set
questions:
  ms-set15-set-1-ms-2021-q01-tossup: [atoms]
  ms-set15-set-1-ms-2021-q04-bonus: [cells, genetics]
```

- The parser applies tags last. A tags file must cover every question in its set; an unknown topic, a missing question or an ID that matches nothing stops the parse.
- A question printed under one of the six disciplines (Energy in any set, or any subject in the 2022 sets) gets that discipline automatically, so a 2022 Chemistry question about humidity is chemistry and earth and space. Every question printed as Energy gets the `energy` discipline, and is tagged with the topic it asks about: a DOE-lab question about lichens is `ecology`, so its disciplines are energy and biology. The energy topics (batteries, fuels, nuclear power, renewables) are for questions about energy itself.
- Keep the topic list broad, so students can practise similar ideas together. A question that fits no topic goes to its discipline's `-misc` topic rather than a new topic. General Science questions are tagged by what they ask about; lab safety, the scientific method and history of science go to the closest discipline's misc (mostly `chemistry-misc`).
- Renaming a topic's label is safe. Changing a topic ID means changing every tags file that uses it.

## Review

```bash
python -m scibowl_qb.parse --level ms --set set15 --no-images
python -m scibowl_qb.tag_review --set set15
```

This writes `output/tag-review-ms-set15.html`: how printed subjects map to disciplines, counts per topic, and every question with its answer, grouped by topic, with filters by discipline and printed subject. To fix a tag, edit the set's file. When the set is right, set `reviewed: true`.

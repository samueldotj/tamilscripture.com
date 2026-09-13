# Tamil drafts

AI translations of the English dictionary articles, produced outside this
repository (docs/feature_dictionary.md §5). One file per article at
`{source}/{slug}.json`:

```json
{
  "id": "eastons/damascus",
  "lang": "ta",
  "source_hash": "d7cd2b5a",
  "generator": { "name": "claude", "model": "…", "prompt_version": "1", "generated_at": "2026-09-20" },
  "title": "தமஸ்கு",
  "paragraphs": [
    { "id": "eastons/damascus#p1-ee1db5fc", "text": "…" }
  ]
}
```

`source_hash` and the paragraph ids come from the build's
`content/{build}/entities/articles/index.json` and `articles/{id}.json`. The
build matches paragraphs by id, requires Tamil script and no markup, and
reports drafts that do not use the accepted Tamil name from `names-ta.toml`.
Drafts of public-domain text are CC BY 4.0; drafts of ShareAlike sources go
under `../ta-sa/`.

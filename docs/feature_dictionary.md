# Feature design: dictionary, people and community review

Milestone M7 in the [README](../README.md#milestones). Status: design, 12 Sep 2026. Nothing here is built.

Builds on the entity foundation in [feature_maps.md](feature_maps.md) §3: the `entity-ingest` crate, the entity model, Tamil name alignment and entity search. This document adds dictionary articles, people, Tamil drafts produced outside the repository, and the community review flow that corrects Tamil names and paragraphs.

## 1. Decisions

| Question | Decision |
|---|---|
| Sources | Reformed sources only. Public-domain candidates: Easton (Matthew George Easton, Presbyterian) and ISBE 1915 (James Orr, United Free Church of Scotland). Smith's (Anglican) and Aquifer are held for the owner's review of sample articles before inclusion. |
| ShareAlike sources | Allowed, kept in their own directories with their own licence files, never merged into a public-domain file. |
| Tamil articles | Drafted in Tamil by an AI process run outside this repository from the English articles, committed as drafts, corrected by the community. English shows only where no Tamil draft exists. |
| Review | Crowdsourced and paragraph-level. Signed-in readers suggest corrections; reviewers edit and accept or reject; moderators also manage roles. Readers see nothing until acceptance. |
| Publishing corrections | Export only. A job every 12 hours exports accepted corrections from the database into the repository, which rebuilds the site. Moderators can trigger it immediately. The site never reads entity content from Postgres. |
| Contribution licence | Suggesting a correction licenses it CC BY, stated on the form and the account page. |
| Moderator notification | The queue page only; no email. |

## 2. Data sources

Same conventions as feature_maps.md §2: one directory per source with `LICENSE`, `SOURCE.md` and the raw download; the build refuses a source without a licence file; licences are verified against the exact file before commit.

| Source | Role | Licence to verify | Directory |
|---|---|---|---|
| Easton's Bible Dictionary | Readable articles for people, places, terms | Public domain | `data/entities/eastons/` |
| ISBE, 1915 edition | Long-form reference articles, shown behind "Read more" | Public domain (US) | `data/entities/isbe/` |
| TIPNR (STEP Bible) | People: identity, disambiguation of same-named people, relations, original-language names, verse links | Open, terms to check per file | `data/entities/tipnr/` (shared with M6) |
| Smith's Bible Dictionary | Additional articles | Public domain edition to confirm | Held pending owner review |
| Aquifer Open Bible Dictionary | Modern readable articles | CC BY-SA, to confirm | Held pending owner review; own directory if approved |
| Theographic knowledge graph | Events, periods, relationships | CC BY-SA, to confirm | Optional, own directory |
| Tamil drafts | AI translations produced outside the repository (§5) | CC BY as translations of public-domain text; `drafts/ta-sa/` for ShareAlike sources | `data/entities/drafts/ta/` |
| Community overrides | Accepted corrections exported from the database (§6) | CC BY | `data/entities/overrides/` |

### Reformed-content gate

Inclusion is decided per source. `data/entities/blocklist.toml` lets the owner exclude individual articles by source and id with a reason; the build drops them and the site never links to them. Ten sample articles each from Smith's and Aquifer are generated for the owner's review before either source is added.

## 3. Articles

### Model

```jsonc
// content/{build}/entities/articles/eastons/damascus.json
{
  "source": "eastons",
  "id": "eastons/damascus",
  "title": "Damascus",
  "lang": "en",
  "licence": "PD",
  "attribution": "Easton's Bible Dictionary, 1897",
  "entities": ["place/damascus"],
  "paragraphs": [
    { "id": "eastons/damascus#p1-9c0e2a77", "text": "The most ancient of Oriental cities; the capital of Syria …" },
    { "id": "eastons/damascus#p2-1b6f03d4", "text": "…" }
  ]
}
```

`content/{build}/entities/articles/index.json` lists every article id, title, source hash and paragraph count so external tools can find what is new or changed.

Articles are linked to entities by name with a review list for ambiguous matches (several people named Simon; a place and a person sharing a name). An entity page shows its Easton article inline and ISBE behind "Read more".

### Paragraph identity

Paragraph-level review needs ids that survive rebuilds. Each English paragraph gets `{source}/{article}#p{n}-{hash8}`, where `hash8` is the first eight hex digits of the SHA-256 of the English paragraph text. A Tamil draft paragraph carries the same id as the English paragraph it translates, and an accepted correction is keyed by it. If the English source is re-segmented, the hash changes and the correction detaches deliberately; the build reports it as an orphaned override for a reviewer to reattach.

## 4. People

People come from TIPNR with `disambiguation` text ("Zechariah, son of Berechiah, the prophet"), `role`, `father`, `tribe` and `period` where provided, verse mentions, and related places and people. They share the entity model in feature_maps.md §3 with `type: "person"` and no `geo`. Tamil name forms come from the same alignment table, drafted per name string so same-named people share a form.

An optional reader setting, **Underline names**, adds a dotted underline to aligned Tamil and English name tokens in the verse text that opens the entity. It is off by default and applied as a pre-paint class so the reading page stays quiet and its layout-shift budget holds.

## 5. Tamil drafts produced outside this repository

The AI translation runs outside the project. The build emits the English articles in the segmented form above; the external process reads them and writes Tamil drafts into `data/entities/drafts/ta/`. Both shapes are fixed here so the two sides can be developed independently.

Output the external process must produce, one file per article:

```jsonc
// data/entities/drafts/ta/eastons/damascus.json
{
  "id": "eastons/damascus",
  "lang": "ta",
  "source_hash": "sha256:…",                       // of the English article file it translated
  "generator": { "name": "claude", "model": "…", "prompt_version": "1", "generated_at": "2026-09-20" },
  "title": "தமஸ்கு",
  "paragraphs": [
    { "id": "eastons/damascus#p1-9c0e2a77", "text": "கிழக்கு நகரங்களில் மிகப் பழமையானது; சீரியாவின் தலைநகரம் …" },
    { "id": "eastons/damascus#p2-1b6f03d4", "text": "…" }
  ]
}
```

Rules the build enforces on drafts:

- same paragraph ids and count as the English source;
- `source_hash` matches the current English file, otherwise the draft is stale and the English paragraph is shown for the changed paragraphs;
- Tamil script present, no HTML;
- names inside a draft should use the accepted Tamil forms from `names-ta.toml`; the external process can read that file as its glossary, and the build reports paragraphs whose names differ so reviewers fix them first.

Drafts of public-domain text are released CC BY. A draft of a CC BY-SA source (if Aquifer is approved) is stored under `drafts/ta-sa/` and keeps the ShareAlike licence.

## 6. Community review

The database is a moderation workspace only. Readers write suggestions into it, reviewers accept them there, and a scheduled export writes the accepted text back into the repository, which rebuilds and deploys. No page reads entity content from Postgres, so the site's static rule and its performance budgets are untouched.

### Roles

| Role | Can |
|---|---|
| reader (default, signed in) | Suggest a correction to a Tamil name or an article paragraph; see own suggestions and their status under `/me/contributions` |
| reviewer | Everything above; open the `/mod` queue; accept a suggestion as written, edit its text and accept the edited version, or reject it with a reason; make a direct correction to any Tamil name or paragraph without a prior suggestion |
| moderator | Everything above; appoint and remove reviewers; trigger "Publish now" |

Editing before acceptance is the normal case: the queue opens every suggestion in an editable field pre-filled with the suggested text, beside the current text and the English source. What is saved is the reviewer's final text. The suggestion keeps the reader's original wording, so the record shows what was proposed, what was published, and who changed it; the reader stays credited under `/me/contributions`. A direct correction by a reviewer is stored as a suggestion authored and accepted by the same person in one step, so it appears in the same history and export.

The owner sets moderators directly in the database. Moderators cannot create other moderators. Role changes go through `set_role(target_user, role)`, which checks the caller is a moderator and the target role is `reader` or `reviewer`, so the rule is enforced in Postgres, not in the UI.

### Tables

```sql
alter table profiles add column role text not null default 'reader'
  check (role in ('reader', 'reviewer', 'moderator'));

create table entity_suggestions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users,
  target text not null,                 -- 'name:IRVTAM:Damascus' or 'article:eastons/damascus#p3-4f2a9c1b'
  current_text text not null,           -- what the user saw, so a stale suggestion is detectable
  suggested_text text not null,
  reason text,
  status text not null default 'open' check (status in ('open', 'accepted', 'rejected')),
  created_at timestamptz not null default now(),
  decided_by uuid references auth.users,
  decided_at timestamptz,
  decision_note text,
  final_text text                       -- what the reviewer published; equals suggested_text when accepted unchanged
);

create table entity_accepted (          -- current accepted text per target; history lives in the log
  target text primary key,
  text text not null,
  suggestion_id uuid references entity_suggestions,
  accepted_by uuid not null references auth.users,
  accepted_at timestamptz not null default now(),
  exported_at timestamptz               -- set by the export job
);

create table moderation_log (
  id bigserial primary key,
  actor uuid not null,
  action text not null,                 -- accept, reject, correct, set_role, publish
  target text,
  detail jsonb,
  at timestamptz not null default now()
);
```

Policies: readers insert suggestions for themselves and select their own; reviewers and moderators select all suggestions and call `accept_suggestion(id, final_text)`, `reject_suggestion(id, note)` and `correct_directly(target, text)`, which are `security definer` functions that write `final_text`, `entity_accepted` and the log; nobody updates rows directly; anon has no access. `accept_suggestion` requires `final_text`, so the edited text is what gets published whether or not it differs from the reader's wording, and the log records both. A suggestion whose `current_text` no longer matches the live text shows as stale in the queue. Limits: twenty open suggestions per user; a suggested text must contain Tamil letters unless the target is a transliterated foreign word, checked in the insert function.

The RLS test suite deferred from M3 (task 3.4) becomes part of this milestone, because reviewer and moderator writes are the first privileged operations in the schema.

### Export

`.github/workflows/export-overrides.yml` runs every 12 hours (`0 */12 * * *`), on `workflow_dispatch` (the Run workflow button in GitHub) and on `repository_dispatch` from the site. It reads `entity_accepted` with the Supabase service key held as a GitHub secret, writes one file per entity under `data/entities/overrides/`, marks the rows `exported_at`, and commits as a bot if anything changed. The commit triggers the normal deploy, so the site changes about ten minutes after an export. Override files are the third input to the build, applied over drafts.

```toml
# data/entities/overrides/place/damascus.toml
[names.IRVTAM]
forms = ["தமஸ்கு"]
accepted_at = 2026-10-03T14:12:00Z

[[paragraphs]]
id = "eastons/damascus#p3-4f2a9c1b"
text = "…"
accepted_at = 2026-10-03T14:20:00Z
```

**Publish now** in `/mod` calls a server route on the site that verifies the caller's Supabase session and moderator role, then sends a `repository_dispatch` to GitHub using a fine-grained personal access token scoped to this repository's Actions, stored as a Vercel environment variable. The action is logged. Because publishing is export-only, a corrected name becomes searchable when the deploy reloads the search table, on the same cadence.

### Badges

Text carries a small badge for its provenance: AI draft, community-corrected, owner-authored. Readers never see open suggestions.

## 7. URLs

| Route | Rendering | Content |
|---|---|---|
| `/person/{slug}` | ISR | Names, disambiguation, family, verses by book, places, articles |
| `/dictionary` | Prerender | Index by source with letter navigation and the language badge |
| `/dictionary/{source}/{id}` | ISR | Article with attribution and licence, links to entities, suggestion controls per paragraph |
| `/me/contributions` | Client-only | A reader's suggestions and their status |
| `/mod` | Client-only, role-gated | Review queue, direct corrections, Publish now |
| `/mod/roles` | Client-only, moderators | Appoint and remove reviewers |
| `/api/mod/publish` | Server | Verifies the moderator session and dispatches the export workflow |

## 8. Search and reader integration

Articles are searchable by title through the entity search table (feature_maps.md §3); Tamil article bodies join the existing full-text search with `tamil_tsvector` once drafts exist. People appear in the search box and reference box suggestions like places.

The context panel and bottom sheet gain **People** and **Dictionary** tabs beside Related verses and Places. The Dictionary tab shows the Easton article for the selected verse's entities with "Read more" for ISBE.

## 9. Performance

- Reading pages: nothing new on the critical path; tabs load their JSON when opened; the name underline setting is off by default.
- Article and person pages: 500 ms target, static content only.
- Moderation pages are client-only and excluded from the reading budgets.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Doctrinal mismatch in individual articles | Source-level gate plus per-article blocklist; owner reviews samples before a source is added |
| A source's file licence differs from the discussion | Task 7.1 verifies each file and records the hash; build refuses missing licences |
| Stale drafts after an English source changes | Source hash check; per-paragraph fallback to English; orphaned overrides reported |
| Low-quality or abusive suggestions | Open-suggestion limit; Tamil-script check; reviewers edit before accepting; log of every decision |
| Privileged writes | All writes through `security definer` functions; RLS test suite covers every role |
| Bad override rewriting files silently | Export commits as a bot with a diff visible in the repository; the build validates every override against the name rule and paragraph ids |

## 11. Owner items

1. Approve or reject Smith's and Aquifer after reading the sample articles (task 7.1).
2. Produce Tamil drafts outside the repository in the §5 shape once the English articles are emitted (task 7.4).
3. When the review flow starts (task 7.7): create the fine-grained GitHub token for Publish now and the Supabase service key secret for the export job. Both are entered by the owner, never handled in chat.

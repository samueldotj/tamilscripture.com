# Feature design: reading plans

Status: built 26 Sep 2026 from design 14A (Claude Design handoff, "Tamil Bible Site Redesign", `Reading Plans.dc.html`).

A reader joins one or more reading plans and gets each day's passages on a Today page. They tick passages off one by one or a whole day at once, catch up on missed days, and follow their progress on a Stats page, as a calendar or a list. Four plans are built in: the whole Bible in one or two years, the New Testament in six months, and the Psalms in six months. Moderators write further community plans, and those appear for everyone once published.

## 1. Decisions

| Question | Decision |
|---|---|
| What a plan is | One to six *tracks* read side by side. Each track is a run of chapters split evenly across the plan's days: day *d* reads units `round(dN/D)` to `round((d+1)N/D)`. When a track has fewer units than there are days, the spare days (rest days) fall evenly through the plan rather than all at the start. The built-in Psalms plan reads Psalm 119 as its 22 stanzas of eight verses. |
| Where plans live | Built-in plans are code (`lib/plans/schedule.ts`) and are never stored. Community plans are rows in `reading_plans`, which hold only the shape: names, length in days, and tracks as ranges of USFM book codes. The daily schedule is always computed in the browser. |
| What progress stores | The start date and the set of passages read, each written as `day-track` (`"12-0"` is the first track on day 13). Rest days need no key. The database checks the key shape, never the text. |
| Signed out | Progress is kept in this browser (`localStorage` key `readingPlans`), so anyone can follow a plan without an account. The Plans page says so and offers sign-in. |
| Signed in | Progress is kept in `plan_progress`, one row per plan, under row-level security like highlights and notes. The first time a signed-in account has no plans but the browser has some, the browser's plans are moved to the account and removed from the browser. |
| Who writes community plans | Moderators only (`my_role() = 'moderator'`), enforced by RLS. Moderators also see drafts; everyone else, including anon, reads published plans only. |
| Where the pages are | `/plans` (Today), `/plans/browse`, `/plans/stats`, all rendered in the browser (`ssr = false`, `noindex`). The editor is at `/mod/plans`: it sits behind the /mod gate, shows as a Plans tab for moderators, and its chunk counts against the staff budget. The plans tab bar shows a MOD link to it for moderators. |
| Links | Footer, avatar menu and phone menu: "வாசிப்புத் திட்டங்கள் / Reading plans". A passage's Read link opens its first chapter in the reader's own version (a Psalm 119 stanza opens as its verse range). |
| Colours | The design's night-slate hex values are mapped to the theme tokens (`--accent`, `--surface-2`, `--good`, `--bad`, …), so the pages follow the light theme too. Calendar "partly" and "missed" cells are `color-mix` tints of `--accent` and `--bad`. |
| Language | Labels follow the interface language (`settings.uiLang`). Plan titles show in that language, with the other language as a kicker or subtitle. Book names come from `books.toml`. |

## 2. Data

Migration `20260926120000_reading_plans.sql`.

`reading_plans`, one row per community plan:

| Column | Meaning |
|---|---|
| `id` | uuid; also the plan's id in `plan_progress.plan` |
| `title_ta`, `title_en` | 120 characters each; a published plan needs a Tamil name |
| `blurb` | 1,000 characters |
| `days` | 7–730 |
| `tracks` | JSON array checked by `check_plan_tracks()`: 1–6 of `{ "name", "from", "to" }` with USFM codes |
| `status` | `draft` or `published` |
| `created_by` | the moderator; set on insert, not updatable |
| `published_at`, `created_at`, `updated_at` | |

`plan_progress`, primary key `(user_id, plan)`:

| Column | Meaning |
|---|---|
| `plan` | a built-in key (`bible-1y`, `bible-2y`, `nt-6m`, `psalms-6m`) or a `reading_plans` uuid |
| `start_date` | the plan's first day, in the reader's calendar |
| `done` | `text[]` of `day-track` keys, checked by `check_plan_done()` (at most 4,380) |

`export_my_data()` now carries `reading_plans` (the reader's progress rows).

## 3. Data flow

- `lib/plans/schedule.ts`: built-in plans, `fromRow()` for community plans, `schedule()` (cached per plan object), labels, dates, `stats()` and `status()`. It has no Svelte and no network code.
- `lib/plans/repo.ts`: `publishedPlans()` is a plain anon REST request, so a signed-out reader never loads supabase-js. It also has `allPlans`, `savePlan` and `deletePlan` for moderators, and `loadProgress`/`saveProgress` (browser or account). Writes for one plan run in order.
- `lib/plans/store.svelte.ts`: one store shared by the three pages. It holds the catalogue, the reader's progress, the active plan (remembered in `localStorage`, `readingPlanActive`) and the selected day. Changes show at once and are saved in the background; a failed save shows an alert on the page.

## 4. Screens

- **Today**: plan chips (when more than one plan is joined), title, progress bar, day number and status, the day card (passages with tick boxes, Read links, Mark day read), missed days (collapsed), and the next three days. ‹ › step through days; a day picked on Stats or in the lists opens here.
- **Plans**: joined plans first, then the rest. Each card shows length, a community tag, both names, the blurb, and chapters per day. Joined cards have progress, Continue and Leave (confirm on second tap). The others have Start today and Start on the first of next month.
- **Stats**: percentage complete, streak, chapters read, estimated finish, a progress bar with a marker for where the reader should be today, and a calendar (a row per month, a cell per day) or a list of every day with its own tick box.
- **Create plans** (`/mod/plans`): the plan list with status, the form (names, description, length, tracks with first and last book), and a live preview of the first seven days with errors. Actions are Publish or Update, Save draft (or Unpublish to draft), and Delete (confirm).

## 5. Budgets

The plan pages are ordinary client routes counted in the site budget (`scripts/size-check.mjs`). The editor is under `/mod` and counts against the staff budget. There are no new static assets.

## 6. Roadmap

- Mark a passage read automatically when its chapter is read to the end in the reader.
- Reminders: a daily notification or e-mail.
- Plans shared by link, and group plans for a church, with the group's progress shown.
- Server-rendered, indexable plan pages for search.

## 7. Risks and checks

- **Editing a published plan moves the schedule under its readers.** Progress keys are day and track indexes, so changing a plan's length or tracks after readers have joined reassigns what they have ticked. The editor does not warn yet; the safe course is to publish a new plan instead.
- **Deleting a community plan** leaves readers' `plan_progress` rows behind. The pages hide them, but they are still in the export.
- **Time zones**: days are the reader's local calendar days; `start_date` has no zone.
- **Checks**: `supabase/tests/reading_plans.test.sql` (pgTAP, in CI) covers the shape checks, moderator-only writes, draft visibility, private progress, anon access, and the export.

## 8. Owner items

- Deploy the migration (`supabase db push` in deploy.yml). Until then `/plans` works with the built-in plans, and signed-in progress cannot be saved.
- Review the English blurbs and labels written for the built-in plans (design 14A had Tamil only).

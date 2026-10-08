# Feature design: site analytics for moderators

Milestone M8 in the [README](../README.md#milestones). Status: phases A1 to A6 built 18 Sep 2026; A7 (audio listening) and A8 (accounts, reading plans, traffic sources) built 26 Sep 2026; A9 (sharing) built 6 Oct 2026.

Moderators need to see how many people use the site and what they read: visitors, page views, unique views, which verses people tap, and where readers are and on what devices. This document fixes what is collected, how it stays private, where it lives, and the order it is built in.

## 1. Decisions

| Question | Decision |
|---|---|
| Build or buy | Build. The About page promises no third-party tracking scripts, reading habits on a Bible site are sensitive (religious belief is special-category data under GDPR, and India's DPDP Act 2023 requires consent for personal data), and moderators already have a role and a `/mod` area. Google Analytics would add a cookie banner, tens of kilobytes of script and a third party. |
| Who sees it | Reviewers and moderators, in `/mod/traffic`, enforced in Postgres (`is_staff()`), like the review queue. |
| Identity | No cookies, no stored IP address, no stored user id. A visitor is a daily-rotating hash; a signed-in user is a separate daily-rotating hash. Nobody can be followed from one day to the next, and no moderator can see what a named person read. |
| "Users" | Counted, not identified: visitors per day, and signed-in users per day, each from its own hash. |
| Country, region, city | From Vercel's edge geolocation headers (`x-vercel-ip-country`, `x-vercel-ip-country-region`, `x-vercel-ip-city`) on the collection request. The IP address is hashed with the day's salt inside Postgres and never written. |
| Device and resolution | Device class, OS and browser from the user-agent on the server; screen resolution (CSS pixels) from the page. |
| Verse clicks | One event when a reader selects a verse (taps its number), with the verse id. |
| Audio listening (A7) | `audio` events from the player: a chapter started (by the reader, from its start or from a verse, or by continuing), a jump to a verse, a chapter heard to its end, and seconds actually listened. Listening time is sent when the chapter changes, the bar closes or the tab is hidden, so time heard in the background counts. Nothing identifies the listener beyond the same daily hash. |
| Sharing (A9) | `share` events when a share went through: a link from the reader's share menu (the verse in its chapter, or the large single-verse page; sent through the share sheet, or copied where there is none), or a verse image from "Share as image" (downloaded, sent through the share sheet, or copied). A share sheet closed without sending is not counted. Images also record their template, size and theme. |
| Opt-out | Browsers that send Global Privacy Control or Do Not Track are not counted at all. |
| Bots | Dropped on the server by user-agent (crawlers, previews, headless browsers, Lighthouse). |
| Retention | Raw events 90 days; daily rollups kept two years (phase A3). A day's salt is deleted the day after, so its hashes become unlinkable. |

## 2. Data flow

```mermaid
flowchart LR
  P["Page (events queued in memory)<br/>sendBeacon when hidden · ≤ 20 events"] -- "POST /api/t<br/>[kind, path, route, verse, screen, referrer, lang, user id?]" --> R["Vercel function /api/t<br/>drop bots · read geo headers · parse UA"]
  R -- "rpc track(…, ip, ua, user)" --> F["Postgres track()<br/>hash with today's salt · rate limit"]
  F --> E[("analytics_events<br/>no IP · no user id")]
  S[("analytics_salt<br/>one row per day")] --> F
  E -- "analytics_report(from, to)<br/>staff only" --> M["/mod/traffic"]
  C["pg_cron"] -. "drop old salts · purge > 90 days" .-> E
```

*Events are sent in one request per visit (when the tab is hidden or closed, or after 20 events) rather than one per event, which keeps Vercel edge requests and function calls down; the function still calls `track()` once per event.*

*The IP address and user id travel to one database function and stop there: it stores only hashes salted with a value that is deleted the next day.*

## 3. What is stored

`analytics_events`, one row per event:

| Column | Meaning |
|---|---|
| `at`, `day` | Time; the day in India time (Asia/Kolkata), which is also the salt's day |
| `kind` | `view`, `verse`, `audio` or `share` (the Android app adds its own kinds) |
| `path`, `route` | URL path without query; SvelteKit route id, so "all chapter pages" can be grouped |
| `verse` | For `verse` events: `JHN.3.16`; for `share`, the first verse shared |
| `book`, `chapter` | For chapter-page views: `JHN`, `3` |
| `visitor` | First 16 hex of sha256(salt ‖ ip ‖ user-agent) |
| `member` | First 16 hex of sha256(salt ‖ user id) for signed-in readers, else null |
| `country`, `region`, `city` | From the edge headers |
| `device`, `os`, `browser` | `mobile` / `tablet` / `desktop`; family names only, no versions |
| `screen` | `390x844` (CSS pixels) |
| `referrer` | On a visit's landing page only (A8): the referring site's host when it is another site (an Android app arrives as its package, `com.whatsapp`, from Chrome's `android-app://` referrer); `utm:<tag>` when the link carried `?utm_source=<tag>`; `facebook.com`, `instagram.com` or `linkedin.com` for those apps' in-app browsers, which send none; `(direct)` for a landing with no referrer. Null on every other event |
| `lang` | Interface language, `ta` or `en` |
| `action` | For `audio`: `play` (a reader started a chapter; `verse` is set when started from a verse), `next` (the next or previous chapter, by itself or by ⏮/⏭), `jump` (to a verse while playing), `end` (heard to the end), `time` (seconds listened). For `share` (A9): `link`, `large` (the reader's share menu), `download`, `sheet`, `copy` (an image) |
| `version` | For `audio`: the recording's version code, `IRVTAM`; for `share`, the first version shown |
| `amount` | For `audio` `time`: seconds listened, 1 to 3,600 |
| `detail` | For an image `share`: template, size and theme, `plate.square.light` |

Nothing in the table identifies a person. `analytics_salt(day, salt)` holds one random salt per day; the collector reads today's, and a daily job deletes older ones.

## 4. What moderators see

`/mod/traffic`, a tab beside the queue:

- a range of 1 day (today so far, India time), 7, 30 or 90 days, or a year;
- a source switch (A10): all traffic, the website only, or the Android app only (`source` on each event); moderators' own pages (`/mod`, `/mod/*`) are never counted;
- a live panel: visitors, views, verse clicks and listeners in the last 30 minutes, the pages being read, the chapters being heard and where from, refreshed every minute;
- tiles: page views, visitors, unique page views, signed-in users, verse clicks, each with its change against the previous period of the same length;
- an Audio Bible row of tiles (A7): chapter plays (`play` + `next`), listeners (per day, summed), listening time, and chapters completed with their share of plays; each also switches the daily chart, which shows listening time in minutes;
- a Sharing row of tiles (A9): shares, sharers (per day, summed) and verses shared as an image; each also switches the daily chart;
- a sign-ups tile (A8, accounts created in the range) beside them, which also switches the chart;
- a daily chart of one chosen measure, with a note on any day above three times the typical day;
- an Accounts card (A8, `analytics_accounts`): accounts in all; signed up, signed in (`auth.users.last_sign_in_at` in the window) and active while signed in (a session used in the window; the site refreshes its token hourly while open) over the last 24 hours, 7 days and 30 days; the peak sign-up day and the peak day for signed-in users, ever and in the range;
- a Reading plans card (A8, `analytics_plans`): signed-in readers on a plan, plans joined, plans started in the range, readers who ticked a passage in the last 7 days, and the plans by readers, most followed first (plans joined while signed out live in that browser and are not counted);
- a grid of the 66 books shaded by chapter-page views;
- tables with bars and CSV export: where visitors come from (A8: every referrer in the range summed by `analytics_source()` into Google, WhatsApp, Facebook, Instagram, YouTube, Telegram, X, LinkedIn, Reddit, Bing, DuckDuckGo, other search engines, email, AI assistants, direct and other sites), top pages, parts of the site, most-read chapters, most-tapped verses, verse clicks by book, search terms, searches with no result, most-played chapters (with version), plays by version, listening time by version, how playback started, verses played from, most-shared verses, how verses were shared, image templates, image sizes, countries, cities, devices, screen resolutions, operating systems, browsers, referring sites, interface language.

Definitions, shown on the page:

- **Visitors** are counted per day and summed over the range, because the daily salt makes the same person on two days two visitors. This over-counts returning readers; it is the price of not tracking them.
- **Unique page views** count each visitor once per page per day.
- **Signed-in users** are counted the same way as visitors, from the member hash.

## 5. Abuse and limits

- The collector is public, as any analytics endpoint must be. `track()` caps each visitor at 600 events a day and rejects malformed input; a determined forger can still add noise, which is accepted.
- Each page view costs one Vercel function call and one insert. At tens of thousands of views a day that is well inside the free tiers; phase A3's rollups keep the table small.
- The page's share is one small module (~1 kB) loaded with the layout, inside the site JavaScript budget. The `/mod` pages have their own 60 kB budget in `scripts/size-check.mjs`, so staff-only code never counts against readers.

## 6. Roadmap

| Phase | What | Status |
|---|---|---|
| **A1 · Collect** | Migration (`analytics_salt`, `analytics_events`, `track()`, retention jobs); `/api/t` with bot filter, geo headers and user-agent parsing; page-view and verse-click beacons; GPC/DNT opt-out; About page privacy text updated | Built 18 Sep 2026 |
| **A2 · Dashboard** | `analytics_report(from, to)` (staff only); `/mod/traffic` with range switch, tiles, daily chart and ranked tables; pgTAP tests for who can read and write | Built 18 Sep 2026 |
| **A3 · Rollups and retention** | `analytics_daily` and `analytics_daily_totals` filled nightly at 06:00 India time by `analytics_rollup_pending()`; the report reads rollups for finished days and live counts for the rest, so a year's range stays fast; raw events purged after 90 days, rollups after two years | Built 18 Sep 2026 |
| **A4 · Reading insight** | Book and chapter recorded with each chapter-page view; books grid, most-read chapters, verse clicks by book, parts of the site (reading, atlas, dictionary, places, people, search…), search terms and searches with no result from `search_log` | Built 18 Sep 2026 |
| **A5 · Live and export** | `analytics_now()` live panel; CSV export of the daily series and every table; change against the previous period on each tile | Built 18 Sep 2026 |
| **A6 · Hardening** | Per-address limit of 60 events a minute in the collector (plus 600 a visitor a day in Postgres), 2 kB body cap, prefetches skipped, wider bot list, spike note on the chart, `scripts/analytics-load.mjs` dry-run load test (about 1,800 requests a second locally) | Built 18 Sep 2026 |
| **A7 · Audio listening** | `audio` events from the Audio Bible player (`action`, `version`, `amount` columns); audio dimensions and totals in the daily rollups; Audio Bible tiles, chart, live listeners and five tables on `/mod/traffic`; migration `20260926100000_audio_analytics.sql`, pgTAP `audio_analytics.test.sql` | Built 26 Sep 2026 |
| **A8 · Accounts, plans, sources** | Landing pages marked in the collector (`(direct)`, `utm:<tag>`, in-app browsers); `analytics_source()`, `analytics_accounts(from, to)` and `analytics_plans(from, to)` (staff only; counts from `auth.users`, `auth.sessions` and `plan_progress`, nobody named); `sources` in the report; sign-ups tile, Accounts and Reading plans cards and a sources table on `/mod/traffic`; migration `20260926130000_accounts_plans_sources.sql`, pgTAP `accounts_plans_sources.test.sql`. Direct visits are counted from this phase on; WhatsApp on iOS sends no referrer, so shared links need `?utm_source=whatsapp` to be credited | Built 26 Sep 2026 |
| **A9 · Sharing** | `share` events from the reader's share menu and "Share as image" (`detail` column for an image's template, size and theme); share dimensions and totals in the daily rollups; Sharing tiles, chart and four tables on `/mod/traffic`; migration `20261006100000_share_analytics.sql`, pgTAP `share_analytics.test.sql` | Built 6 Oct 2026 |
| **A10 · Source filter, 1 day** | A 1-day range; the beacon sends nothing from `/mod` and the summaries skip `/mod` events already stored (`analytics_counted()`); rollups kept per `source` (`web`, `android`), summed for "all"; `analytics_report(from, to, source)` and `analytics_now(source)` take an optional source; a source switch on `/mod/traffic`. Days whose raw events are still held (90 days) are rolled up again by the migration; older summaries keep any `/mod` views. Search terms, accounts and plans are not split by source; migration `20261007100000_traffic_source_filter.sql`, pgTAP `traffic_source_filter.test.sql` | Built 7 Oct 2026 |
| **Next** | Countries on a map; per-page drill-down; alert moderators on the queue page when a day spikes | Ideas |

## 7. Owner items

None for A1 and A2: collection uses the existing public key and Vercel's own headers. A3's nightly job runs in Postgres with pg_cron, which the project already uses.

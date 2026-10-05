# Plan: moving static content from Vercel to R2

Status: proposal 3 Oct 2026, not built.

The question was whether the Bible text, cross-references, entity data and search CSVs should leave the Vercel deployment and be served from Cloudflare R2, the way the audio and the commentary already are. The deciding factors are page speed and monthly cost. Uploads are one-off scripts run on the owner's machine, the same as `tools/audio` and `bible-commentaries/tools/publish.py`.

## 1. Summary

| Content | Size, files | Move? | Why |
|---|---|---|---|
| Entity data (`entities/`: articles, Strong's, original, maps, people, places, mentions, geo) | 228 MB, ~39,000 files | **Yes, first** | Two thirds of the deployment. It is used off the reading path (study panel, atlas, person, place and dictionary pages), so a Cloudflare outage would not stop anyone reading. |
| Bible text (5 versions) | 72 MB, ~6,000 files | **Later, optional** | Small. It's also the one thing the site promises always to serve ("reading never depends on…", design §1). Moving it puts reading behind Cloudflare. |
| Cross-references (`xref/`) | 14 MB, 1,189 files | With the Bible text | Loaded with every chapter, so it shares the text's availability concerns. |
| Search CSVs (`search/`) | 42 MB, 6 files | **No** | They are never on Vercel. `deploy.yml` deletes `static/content/*/search` before upload, and the CSVs only feed Postgres through `scripts/load-search.sh`. Moving them gains nothing. |
| `manifest.json` | 24 kB | No | Bundled into the app via `$content/manifest.json`. |

**Recommendation:** move the entities in phase 1. Keep the Bible text and cross-references on Vercel, and set long browser caching on them (§5, step 0), which gets most of R2's speed benefit for free. Revisit the text only if Vercel usage limits come into view.

The monthly cost is about **$0 either way** at the site's current scale. R2's free tier covers this content many times over, and the Vercel bytes it frees are small. The real benefits are deploy size and time (about 310 MB and 40,000 fewer files per deploy), headroom under Vercel's request and bandwidth limits, and immutable browser caching.

## 2. How content is served today (measured 3 Oct 2026)

- Paths are `/content/{build}/...` (`contentUrl` in `lib/content/manifest.ts`). The build id hashes **only the Bible sources**. Entity files change between deploys under the same build id, which is why the service worker fetches them network first.
- Vercel returns `Cache-Control: public, max-age=0, must-revalidate` for every content file (`x-vercel-cache: HIT`, brotli). The edge caches it, but the browser revalidates on every reuse. The service worker avoids that for chapter JSON, which it serves cache first, but not for entities.
- On the first visit to a chapter, the HTML comes from ISR with the chapter JSON already inlined, so the browser makes **no** content request. Content requests happen on client-side navigation (chapter and xref JSON) and on entity pages and panels.
- R2 at `stream.tamilaudiobible.com` already does what this plan needs. JSON is edge-cached (`cf-cache-status: HIT`), CORS allows `https://www.tamilscripture.com`, and the commentary objects are sent with `max-age=31536000, immutable`. One sample from the owner's machine took 471 ms on a cold connection and 57 ms on a warm one. Vercel took 52 ms.
- In 30 days there were 20 commits to `data/entities` and 23 to `crates/entity-ingest`, against 4 to `crates/usfm-ingest` and 5 to `data/versions`. Entities have been the busiest content recently (last change 27 Sep), so "rarely changes" holds for the text but only lately for entities.

## 3. Load speed: pros and cons

| Situation | Vercel today | R2 | Net |
|---|---|---|---|
| First visit to a chapter (HTML via ISR) | HTML with JSON inlined | Unchanged: the HTML stays on Vercel | **No change** |
| First render of a page after a deploy (ISR miss) | Function in bom1 reads the JSON from Vercel | Function fetches from Cloudflare. Mumbai to Mumbai PoP is a few ms; a Cloudflare miss going to the bucket can take 100–300 ms. | **Slightly slower**, once per page per deploy, and readers don't see it |
| Client navigation to the next chapter, first time this session | Same connection as the page (HTTP/2 reuse) | A second origin needs DNS, TCP and TLS: about 100–300 ms on Indian mobile networks | **Slower once per session.** `<link rel="preconnect">` for the R2 host hides most of it. |
| The same, after that | Edge hit, ~50 ms | Edge hit, ~50 ms. Cloudflare has more PoPs in India (Chennai, Bengaluru, Hyderabad and others) than Vercel, which helps readers in Tamil Nadu. | **Same or slightly faster** |
| Opening a file the browser already has | Revalidation round trip (`max-age=0`), a 304 | `immutable`: served from disk, 0 ms | **Faster.** Vercel can match this with a header (step 0). |
| Long-tail entity files (13,000 articles, 17,000 Strong's) | Edge miss goes to Vercel's origin store | Edge miss goes to R2 origin. Cloudflare's free plan evicts cold files sooner. | **About the same.** Turn on Tiered Cache (free) to improve it. |
| Offline (service worker) | Content is cached | **Broken until the SW changes:** it ignores cross-origin requests (`url.origin !== sw.location.origin`) | Must be fixed in phase 1 (§5) |
| Cookies on content requests | Sent (same site) | Not sent | Tiny gain |

In short, R2 is not faster for first loads. It can be slightly slower on the first navigation of a session unless you preconnect. It is faster on repeat visits only because of immutable caching, which Vercel can also provide.

## 4. Monthly cost: pros and cons

**R2** (list prices; check before relying on them). Storage is 10 GB a month free, then $0.015/GB. Class A (writes) is 1 M a month free, then $4.50/M. Class B (reads) is 10 M a month free, then $0.36/M. Egress is free. Requests answered from Cloudflare's cache are not R2 reads.

| Item | Phase 1 (entities) | Phase 2 (+ text, xref) |
|---|---|---|
| Storage per published version | 0.23 GB | 0.31 GB |
| Keeping 10 old versions | 2.3 GB | 3.1 GB |
| Writes per full upload | ~39,000 | ~46,000 |
| Full uploads before the free tier runs out | ~25 a month | ~21 a month |
| Reads | Cache misses only, well under 10 M | Same |
| **Monthly cost** | **$0** | **$0** |

**Vercel.** Moving content off does not lower a bill unless you are near a limit. On Hobby, the limits to watch are Fast Data Transfer (100 GB), Edge Requests (1 M, which counts every 304 and every JS chunk) and ISR reads and writes. Pro includes much more, and charges per GB and per million requests beyond that. Here is a rough guide to what this content costs Vercel today:

| Monthly page views | Content requests (≈2 per client navigation, ~60% of views) | Content bytes (brotli, ~5 kB each) |
|---|---|---|
| 100,000 | ~120,000 | ~0.6 GB |
| 1,000,000 | ~1.2 M | ~6 GB |

The HTML, JS and fonts stay on Vercel and make up most of the bytes. The content's share of Edge Requests is what matters on Hobby: at about a million page views a month, content JSON alone reaches the 1 M request limit. Use the Usage page in Vercel to compare the real numbers against these.

**Other cost effects**

- Deploys: dropping 228 MB and 39,000 files from every `--archive=tgz` upload shortens the deploy job and keeps the deployment away from per-deployment file limits.
- The ISR cache is still emptied on every deploy (deploy.yml comment), so ISR writes are unchanged.
- CI still builds all content, because the manifest and search CSVs depend on it. It just doesn't ship most of it.

**Main drawbacks**

- **Availability.** Today `tamilscripture.com` never depends on Cloudflare (feature_audio.md §1). After phase 1, a Cloudflare outage breaks study panels, maps, the atlas and entity pages, but not reading. After phase 2 it also breaks chapter navigation, and ISR renders of chapters after a deploy. This is why the text is optional.
- **Version drift.** The site and R2 can disagree: a deploy can reference a version that was never uploaded. The guard in step 3 prevents this.
- **A second release step.** Entity changes have been frequent. Each one now also needs an upload before or with the deploy.

## 5. Migration steps

**Step 0, on Vercel and independent of R2.** Add `Cache-Control: public, max-age=31536000, immutable` for `/content/{build}/*` other than `entities/`. Text and xref are already immutable per build id. Confirm that `vercel build` with adapter-vercel applies `vercel.json` `headers`, or set them in the adapter output. This is the cheapest speed gain in the plan.

**Step 1, version entities by content.** In `entity-ingest`, or a small script after it, compute `ebuild` = the first 10 hex characters of a SHA-256 over every file under `entities/`, sorted by path. Write it to `manifest.json` as `entities_build`. The output must be byte-deterministic, as the Bible build already is.

**Step 2, one-off upload script** (`scripts/publish-content.py`, modelled on `bible-commentaries/tools/publish.py`: boto3, `R2_*` from the environment, parallel puts):

- Keys: `content/entities/{ebuild}/...`, and later `content/{build}/{VERSION|xref}/...`. They sit in the existing `ts-audio` bucket under `stream.tamilaudiobible.com`, so the browser shares one connection with audio and commentary. A separate `content` bucket on its own subdomain works too, but costs a third connection.
- `Content-Type: application/json; charset=utf-8` (`image/svg+xml` for maps), `Cache-Control: public, max-age=31536000, immutable`.
- Skip a version that already exists, never overwrite, and write `{ebuild}/_complete` last.
- `--dry-run` reports counts and bytes, and `--verify` HEADs every key.

**Step 3, site changes:**

- `PUBLIC_CONTENT_BASE`, like `PUBLIC_COMMENTARY_BASE`, with a default of `/content` so local dev and the Node adapter serve from `static/` as now. Add an `entityUrl(path)` beside `contentUrl`, and switch `lib/entities/*.ts`, `atlas/basemap.ts` and the other `entities/` callers to it.
- Service worker: also handle requests to the R2 origin. Entity paths now carry `ebuild`, so they can move from network first to **cache first**, which makes entities faster than they are today. Bump `CONTENT` to `content-v3`.
- `<link rel="preconnect" href="https://stream.tamilaudiobible.com" crossorigin>` in `app.html`.
- `deploy.yml`, before the Vercel build: check that `{base}/entities/{ebuild}/_complete` exists and fail the deploy if it doesn't. Then `rm -rf static/content/*/entities`. The site can't ship pointing at content that isn't there.

**Step 4, roll out.** Run the upload and `--verify`. Deploy. Check the network panel: an entity request goes to `stream.`, `cf-cache-status` is HIT on the second try, and CORS passes. Check that the place, person, Strong's and atlas pages, offline, all work. Keep the old Vercel deployment as an instant rollback in Vercel's dashboard.

**Step 5, later and optional (Bible text and xref).** Use the same pattern under the existing `build` id. Upload whenever `build` changes; at 4 Bible-source commits a month, that's rare. ISR server loads fetch the absolute URL; the comment in `chapter-load.ts` about "no network" changes. Decide on this only after weighing the availability drawback above.

## 6. Rollback

Set `PUBLIC_CONTENT_BASE` back to `/content` (or empty), remove the `rm -rf` and the R2 check from `deploy.yml`, and redeploy. Objects on R2 are never overwritten, so any earlier site version that points at them keeps working.

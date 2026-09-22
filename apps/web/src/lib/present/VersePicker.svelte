<script lang="ts">
	// The right panel of the editor (design 11A): the verses on this slide,
	// each with its version, and ways to add more: a reference or a word
	// typed into the box, the slide's cross-references, what the author read
	// recently, and their highlights.
	import { ready, parseReference } from '$lib/ref/client';
	import { chapterCached, lastVerse, verseList, versesText } from '$lib/content/verses';
	import { loadXrefs } from '$lib/content/load';
	import { chapterUrl, findBook, findVersion, manifest } from '$lib/content/manifest';
	import type { XrefChapter } from '$lib/content/types';
	import { search } from '$lib/search/api';
	import { allHighlights, history } from '$lib/personal/repo';
	import { LIMITS, verseKey, verseLabel, verseVersion, type Slide, type SlideVerse } from './types';

	let {
		slide,
		version,
		lang = 'ta',
		onadd,
		onremove,
		onversion
	}: {
		slide: Slide;
		/** The presentation's default version code. */
		version: string;
		lang?: 'ta' | 'en';
		onadd: (v: SlideVerse) => void;
		onremove: (index: number) => void;
		onversion: (index: number, code: string | undefined) => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	const meta = $derived(findVersion(version) ?? manifest.versions[0]);
	const full = $derived(slide.verses.length >= LIMITS.versesPerSlide);
	const onSlide = $derived(new Set(slide.verses.map(verseKey)));

	type Candidate = { v: SlideVerse; tag?: string };
	type Tab = 'xrefs' | 'recent' | 'highlights';
	let query = $state('');
	let busy = $state(false);
	let hint = $state('');
	let results = $state<Candidate[]>([]);
	let chapterPick = $state<{ book: string; chapter: number; verses: { n: string; text: string }[] } | null>(null);
	let tab = $state<Tab>('xrefs');
	let recent = $state<Candidate[] | null>(null);
	let highlights = $state<Candidate[] | null>(null);
	let xrefs = $state<Candidate[]>([]);
	let input = $state<HTMLInputElement>();

	// Verse text for the cards, loaded once per verse and version.
	let texts = $state<Record<string, { text: string; max: number }>>({});
	function textKey(v: SlideVerse) { return `${verseKey(v)}@${verseVersion(v, version)}`; }
	function ensure(v: SlideVerse) {
		const key = textKey(v);
		if (key in texts) return;
		texts[key] = { text: '', max: 0 };
		chapterCached(fetch, verseVersion(v, version), v.book, v.chapter)
			.then((ch) => { texts[key] = { text: versesText(ch, v.start, v.end), max: lastVerse(ch) }; })
			.catch(() => { texts[key] = { text: ta ? 'ஏற்ற முடியவில்லை' : 'Could not load', max: 0 }; });
	}
	const listed = $derived(tab === 'xrefs' ? xrefs : tab === 'recent' ? (recent ?? []) : (highlights ?? []));
	$effect(() => { for (const c of [...results, ...listed]) ensure(c.v); });

	function label(v: SlideVerse) { return verseLabel(v, (findVersion(verseVersion(v, version))?.lang ?? meta.lang)); }
	function readerHref(v: SlideVerse) {
		const book = findBook(v.book);
		return book ? chapterUrl(verseVersion(v, version), book, v.chapter, v.end > v.start ? `${v.start}-${v.end}` : `${v.start}`) : '/';
	}
	function add(v: SlideVerse) {
		if (full || onSlide.has(verseKey(v))) return;
		onadd({ book: v.book, chapter: v.chapter, start: v.start, end: v.end });
	}
	/** Widen or narrow a result's range by one verse at either end. */
	function adjust(i: number, at: 'start' | 'end', by: number) {
		const v = results[i].v;
		const max = texts[textKey(v)]?.max || 176;
		const next = { ...v, [at]: Math.max(1, Math.min(max, v[at] + by)) };
		if (next.end < next.start) return;
		results[i] = { ...results[i], v: next };
	}

	async function submit(e?: Event) {
		e?.preventDefault();
		const q = query.trim();
		if (!q) return;
		busy = true;
		hint = '';
		chapterPick = null;
		try {
			await ready();
			const r = parseReference(q);
			if (r && findBook(r.code)) {
				if (r.verse) {
					results = [{ v: { book: r.code, chapter: r.chapter, start: r.verse, end: Math.max(r.verse, r.verse_end ?? r.verse) } }];
				} else {
					// A chapter alone: list its verses to pick from.
					const ch = await chapterCached(fetch, version, r.code, r.chapter);
					results = [];
					chapterPick = { book: r.code, chapter: r.chapter, verses: verseList(ch, 1, 999) };
				}
			} else {
				const res = await search(fetch, q, [version]);
				results = res.hits.slice(0, 12).map((h) => {
					const [b, c, v] = h.verse_id.split('.');
					return { v: { book: b, chapter: Number(c), start: Number(v), end: Number(v) }, tag: ta ? 'சொல்' : 'word' };
				});
				if (!results.length) hint = ta ? 'ஒன்றும் கிடைக்கவில்லை · எ.கா. ரோமர் 5:8' : 'Nothing found · e.g. Romans 5:8';
			}
		} catch {
			hint = ta ? 'தேட முடியவில்லை' : 'The search failed';
		} finally {
			busy = false;
		}
	}

	// Cross-references of the verses on this slide, most voted first.
	const xrefCache = new Map<string, Promise<XrefChapter>>();
	$effect(() => {
		const verses = slide.verses.map((v) => ({ ...v }));
		let live = true;
		(async () => {
			const seen = new Set<string>();
			const found: { c: Candidate; votes: number }[] = [];
			for (const v of verses) {
				const key = `${v.book}.${v.chapter}`;
				if (!xrefCache.has(key)) xrefCache.set(key, loadXrefs(fetch, v.book, v.chapter));
				let x: XrefChapter;
				try { x = await xrefCache.get(key)!; } catch { continue; }
				for (let n = v.start; n <= v.end; n++) {
					for (const t of x[`${v.book}.${v.chapter}.${n}`] ?? []) {
						const [b, c, s] = t.to.split('.');
						const end = t.end?.split('.');
						const sv: SlideVerse = { book: b, chapter: Number(c), start: Number(s), end: end && end[1] === c ? Number(end[2]) : Number(s) };
						const k = verseKey(sv);
						if (seen.has(k) || !findBook(b)) continue;
						seen.add(k);
						found.push({ c: { v: sv, tag: ta ? 'ஒப்புவசனம்' : 'cross-ref' }, votes: t.votes });
					}
				}
			}
			if (live) xrefs = found.sort((a, b) => b.votes - a.votes).slice(0, 15).map((f) => f.c);
		})();
		return () => { live = false; };
	});

	async function open(t: Tab) {
		tab = t;
		if (t === 'recent' && recent === null) {
			try {
				const seen = new Set<string>();
				recent = (await history(60))
					.filter((h) => h.verse_start)
					.map((h) => ({ v: { book: h.book, chapter: h.chapter, start: h.verse_start!, end: h.verse_end ?? h.verse_start! }, tag: ta ? 'சமீபம்' : 'recent' }))
					.filter((c) => !seen.has(verseKey(c.v)) && seen.add(verseKey(c.v)))
					.slice(0, 15);
			} catch { recent = []; }
		}
		if (t === 'highlights' && highlights === null) {
			try {
				highlights = (await allHighlights())
					.sort((a, b) => b.updated_at.localeCompare(a.updated_at))
					.slice(0, 20)
					.map((h) => ({ v: { book: h.book, chapter: h.chapter, start: h.verse_start, end: h.verse_end }, tag: ta ? 'அடிக்கோடு' : 'highlight' }));
			} catch { highlights = []; }
		}
	}
</script>

{#snippet card(c: Candidate, i: number)}
	{@const key = verseKey(c.v)}
	{@const here = onSlide.has(key)}
	<li class="card" class:here>
		<div class="row">
			<span class="ref" lang={findVersion(verseVersion(c.v, version))?.lang ?? 'ta'}>{label(c.v)}</span>
			{#if c.tag}<span class="tag">{c.tag}</span>{/if}
			<span class="grow"></span>
			<button type="button" class="chip add" class:primary={i === 0 && !here} disabled={full || here} onclick={() => add(c.v)}>{here ? (ta ? 'சேர்ந்தது' : 'Added') : `+ ${ta ? 'சேர்' : 'Add'}`}</button>
		</div>
		<p class="text" lang={findVersion(verseVersion(c.v, version))?.lang ?? 'ta'}>{texts[textKey(c.v)]?.text || '…'}</p>
		<div class="more">
			{#if i >= 0}
				<button type="button" onclick={() => adjust(i, 'start', -1)} disabled={c.v.start <= 1} title={ta ? 'முந்தைய வசனம்' : 'Previous verse'}>◂ {c.v.start - 1 || ''}</button>
				<button type="button" onclick={() => adjust(i, 'end', 1)} disabled={!!texts[textKey(c.v)]?.max && c.v.end >= texts[textKey(c.v)].max} title={ta ? 'அடுத்த வசனம்' : 'Next verse'}>{c.v.end + 1} ▸</button>
			{/if}
			<a href={readerHref(c.v)} target="_blank" rel="noopener">{ta ? 'அதிகாரத்தில் திற' : 'Open in reader'}</a>
		</div>
	</li>
{/snippet}

<section class="on-slide">
	<h3 class="kicker"><span lang="ta">இந்த ஸ்லைடில்</span> · On this slide <span class="count">{slide.verses.length}</span></h3>
	{#if slide.verses.length}
		<ul class="verses">
			{#each slide.verses as v, i (verseKey(v) + i)}
				{@const code = verseVersion(v, version)}
				<li>
					<div class="who">
						<span class="ref" lang={findVersion(code)?.lang ?? 'ta'}>{label(v)}</span>
						<span class="sub">{findVersion(code)?.short} · {findVersion(code)?.lang === 'ta' ? 'தமிழ்' : 'English'}</span>
					</div>
					<select class="ver" aria-label={ta ? 'மொழிபெயர்ப்பு' : 'Version'} value={v.version ?? ''} onchange={(e) => onversion(i, (e.currentTarget as HTMLSelectElement).value || undefined)}>
						<option value="">{meta.short} · {ta ? 'இயல்பு' : 'default'}</option>
						{#each manifest.versions as ver (ver.code)}
							<option value={ver.code}>{ver.short}</option>
						{/each}
					</select>
					<button type="button" class="x" aria-label={ta ? 'நீக்கு' : 'Remove'} onclick={() => onremove(i)}>×</button>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்னும் வசனம் இல்லை. கீழே தேடிச் சேர்க்கவும்.' : 'No verses yet. Search below to add one.'}</p>
	{/if}
</section>

<section class="adder">
	<h3 class="kicker"><span lang="ta">வசனம் சேர்</span> · Add verses</h3>
	<form class="box" onsubmit={submit} role="search">
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7.5" /><path d="m20.5 20.5-4.2-4.2" /></svg>
		<input bind:this={input} bind:value={query} type="search" autocomplete="off" spellcheck="false" enterkeyhint="search" aria-label={ta ? 'வசனக் குறிப்பு, சொல் அல்லது சொற்றொடர்' : 'Reference, word or phrase'} placeholder={ta ? 'ரோமர் 5:8' : 'Romans 5:8'} onfocus={() => ready()} />
		<span class="hint-in">{ta ? 'குறிப்பு, சொல்' : 'ref, word or phrase'}</span>
	</form>
	{#if hint}<p class="hint" role="status">{hint}</p>{/if}
	{#if busy}<p class="muted" aria-busy="true">…</p>{/if}
	{#if results.length}
		<ul class="cards">{#each results as c, i (verseKey(c.v))}{@render card(c, i)}{/each}</ul>
	{/if}
	{#if chapterPick}
		{@const book = findBook(chapterPick.book)}
		<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? `${book?.name_ta} ${chapterPick.chapter} · வசனத்தைத் தேர்ந்தெடுக்கவும்` : `${book?.name_en} ${chapterPick.chapter} · pick a verse`}</p>
		<ul class="cards chapter">
			{#each chapterPick.verses as v (v.n)}
				{@const sv = { book: chapterPick.book, chapter: chapterPick.chapter, start: Number(v.n.split('-')[0]), end: Number(v.n.split('-').pop()) }}
				<li class="card small">
					<div class="row">
						<span class="ref">{v.n}</span>
						<p class="text" lang={meta.lang}>{v.text}</p>
						<button type="button" class="chip add" disabled={full || onSlide.has(verseKey(sv))} onclick={() => add(sv)}>+</button>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
	<div class="tabs" role="tablist">
		<button type="button" role="tab" aria-selected={tab === 'xrefs'} class:on={tab === 'xrefs'} onclick={() => open('xrefs')} lang="ta">ஒப்புவசனங்கள்</button>
		<button type="button" role="tab" aria-selected={tab === 'recent'} class:on={tab === 'recent'} onclick={() => open('recent')} lang="ta">சமீபத்தில்</button>
		<button type="button" role="tab" aria-selected={tab === 'highlights'} class:on={tab === 'highlights'} onclick={() => open('highlights')} lang="ta">அடிக்கோடுகள்</button>
	</div>
	{#if tab !== 'xrefs' && (tab === 'recent' ? recent : highlights) === null}
		<p class="muted" aria-busy="true">…</p>
	{:else if !listed.length}
		<p class="muted" lang={ta ? 'ta' : 'en'}>
			{#if tab === 'xrefs'}{ta ? 'ஸ்லைடில் வசனம் சேர்த்தால் அதன் ஒப்புவசனங்கள் இங்கே வரும்.' : 'Cross-references of the verses on this slide appear here.'}
			{:else if tab === 'recent'}{ta ? 'சமீபத்தில் வாசித்த வசனங்கள் இல்லை.' : 'No recently read verses.'}
			{:else}{ta ? 'அடிக்கோடுகள் இல்லை.' : 'No highlights yet.'}{/if}
		</p>
	{:else}
		<ul class="cards">{#each listed as c, i (verseKey(c.v))}{@render card(c, -1 - i)}{/each}</ul>
	{/if}
</section>

<style>
	section { padding: 1rem 1.25rem; display: flex; flex-direction: column; gap: 0.75rem; }
	.on-slide { border-bottom: var(--bw) solid var(--line); }
	.kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.06em; }
	.count { color: var(--ink); margin-left: 0.3rem; }
	.verses { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
	.verses li { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px; background: var(--surface); border: var(--bw) solid var(--line-2); }
	.who { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
	.ref { font-family: var(--sans); font-size: 1rem; font-weight: 600; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.sub { font-size: 0.72rem; color: var(--muted); }
	.ver { font: inherit; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 4px 8px; max-width: 7rem; }
	.x { width: 28px; height: 28px; border: 0; border-radius: 8px; background: none; color: var(--muted); font-size: 1.1rem; cursor: pointer; }
	.x:hover { background: var(--surface-3); color: var(--ink); }
	.muted { color: var(--muted); margin: 0; font-size: 0.85rem; }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.box { display: flex; align-items: center; gap: 10px; background: var(--surface); border: var(--bw) solid var(--accent); border-radius: 12px; padding: 0 14px; color: var(--muted); }
	.box input { flex: 1; min-width: 0; border: 0; background: none; padding: 11px 0; font-family: var(--tamil); font-size: 1rem; color: var(--ink); }
	.box input:focus-visible { outline: 0; }
	.box input::-webkit-search-cancel-button { -webkit-appearance: none; }
	.hint-in { font-size: 0.68rem; white-space: nowrap; }
	.hint { margin: 0; font-size: 0.8rem; color: var(--amber); font-family: var(--tamil); }
	.tabs { display: flex; gap: 6px; flex-wrap: wrap; }
	.tabs button { font-size: 0.78rem; font-weight: 700; color: var(--ink-2); border: var(--bw) solid var(--line-2); background: none; border-radius: 999px; padding: 5px 11px; cursor: pointer; font-family: var(--tamil); }
	.tabs button.on { color: var(--on-accent); background: var(--accent); border-color: var(--accent); }
	.cards { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
	.card { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-radius: 12px; border: var(--bw) solid var(--line); }
	.card.here { opacity: 0.6; }
	.card .row { display: flex; align-items: center; gap: 8px; }
	.card .grow { flex: 1; }
	.tag { font-size: 0.68rem; color: var(--muted); }
	.card .text { margin: 0; font-family: var(--tamil); font-size: 0.95rem; line-height: 1.6; color: var(--ink-2); text-wrap: pretty; }
	.card .text[lang='en'] { font-family: var(--en); font-size: 0.9rem; }
	.card.small { padding: 8px 10px; }
	.card.small .text { flex: 1; font-size: 0.85rem; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
	.card.small .ref { width: 2.2rem; flex: none; color: var(--accent); font-size: 0.8rem; }
	.add { min-height: 32px; padding: 0.25rem 0.7rem; font-size: 0.8rem; font-weight: 800; border-radius: 8px; }
	.more { display: flex; gap: 6px; flex-wrap: wrap; font-size: 0.72rem; font-weight: 700; color: var(--muted); }
	.more button, .more a { border: 1px solid var(--line-2); border-radius: 6px; padding: 2px 7px; background: none; color: inherit; font: inherit; cursor: pointer; text-decoration: none; }
	.more button:disabled { opacity: 0.4; cursor: default; }
	.more button:not(:disabled):hover, .more a:hover { color: var(--accent); border-color: var(--accent); }
	.chapter { max-height: 24rem; overflow: auto; }
</style>

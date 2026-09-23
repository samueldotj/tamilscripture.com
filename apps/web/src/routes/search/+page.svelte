<script lang="ts">
	import { goto } from '$app/navigation';
	import { bookNameIn, chapterUrl, findBook, findVersion, manifest } from '$lib/content/manifest';
	import { rangeLabel, rangeParams, type SearchRange } from '$lib/search/range';
	import { entityHref, entityKind, entityLabelTa, queryTokens } from '$lib/search/api';
	import { settings } from '$lib/settings/store.svelte';
	import { addRecent } from '$lib/search/recent';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	let q = $state('');
	$effect(() => { q = data.q; });
	// Every search that reaches this page, however it was started, joins the recent list.
	$effect(() => { if (data.q) addRecent(data.q); });

	/** A search URL that keeps the current query, version, scope and range unless told otherwise. */
	function searchHref(over: { q?: string; scope?: string; range?: SearchRange | null; offset?: number } = {}) {
		const range = over.range === undefined ? data.range : over.range;
		const p = new URLSearchParams({ q: over.q ?? data.q, v: data.primary.code, scope: over.scope ?? data.scope, ...rangeParams(range) });
		if (over.offset) p.set('offset', String(over.offset));
		return `/search?${p}`;
	}
	function submit(e: Event) {
		e.preventDefault();
		if (q.trim().length < 2) return;
		goto(searchHref({ q: q.trim() }));
	}
	function setScope(scope: string) {
		goto(searchHref({ scope }));
	}

	// ---- Search in (R-5.8): testament, book, chapters ----
	function setIn(key: string) {
		const p = new URLSearchParams({ q: data.q, v: data.primary.code, scope: data.scope });
		if (key) p.set('in', key);
		goto(`/search?${p}`);
	}
	let chFrom = $state('');
	let chTo = $state('');
	$effect(() => {
		chFrom = data.range?.chMin ? String(data.range.chMin) : '';
		chTo = data.range?.chMax && data.range.chMax !== data.range.chMin ? String(data.range.chMax) : '';
	});
	function setChapters(e: Event) {
		e.preventDefault();
		if (!data.range?.book) return;
		const p = new URLSearchParams({ q: data.q, v: data.primary.code, scope: data.scope, in: data.range.key });
		const a = Number(chFrom), b = Number(chTo || chFrom);
		if (a >= 1) p.set('ch', b > a ? `${a}-${b}` : `${a}`);
		goto(`/search?${p}`);
	}
	const otBooks = manifest.books.filter((b) => b.testament === 'OT');
	const ntBooks = manifest.books.filter((b) => b.testament === 'NT');

	// Group hits by book in canonical order.
	const groups = $derived.by(() => {
		if (!data.result) return [];
		const map = new Map<number, typeof data.result.hits>();
		for (const h of data.result.hits) {
			if (!map.has(h.book_ord)) map.set(h.book_ord, []);
			map.get(h.book_ord)!.push(h);
		}
		return [...map.entries()].sort((a, b) => a[0] - b[0]);
	});
	// Emphasis follows what was searched: the Tamil reading of a romanised query.
	const tokens = $derived(queryTokens(data.shown));

	// Split verse text into plain and matched runs for emphasis.
	function mark(text: string): { t: string; hit: boolean }[] {
		if (!tokens.length) return [{ t: text, hit: false }];
		const re = new RegExp(`(${tokens.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'giu');
		return text.split(re).filter(Boolean).map((t) => ({ t, hit: re.test(t) && (re.lastIndex = 0) === 0 }));
	}
	function refOf(hit: { verse_id: string; version: string }) {
		const [code, ch, v] = hit.verse_id.split('.');
		const book = findBook(code)!;
		const version = findVersion(hit.version)!;
		return {
			label: `${bookNameIn(book, version)} ${ch}:${v}`,
			href: chapterUrl(hit.version.toLowerCase(), book, Number(ch), v),
			lang: version.lang,
			short: version.short
		};
	}
	const pageSize = 50;
</script>

<svelte:head>
	<title>{data.q ? `${data.q} · ` : ''}{ta ? 'தேடல்' : 'Search'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="search">
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'தேடல்' : 'Search'}</h1>

	<form class="searchform" role="search" onsubmit={submit}>
		<div class="box">
			<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7.5" /><path d="m20.5 20.5-4.2-4.2" /></svg>
			<input class="field" type="search" bind:value={q} lang={data.primary.lang} placeholder={ta ? 'சொல் அல்லது "சொற்றொடர்"' : 'word or "exact phrase"'} aria-label={ta ? 'தேடு' : 'Search'} autocomplete="off" />
		</div>
		<button type="submit" class="chip primary">{ta ? 'தேடு' : 'Search'}</button>
	</form>

	<div class="scope" role="radiogroup" aria-label={ta ? 'எங்கே தேட' : 'Search in'}>
		<button type="button" role="radio" aria-checked={data.scope === 'version'} class:on={data.scope === 'version'} onclick={() => setScope('version')}>{data.primary.short}</button>
		<button type="button" role="radio" aria-checked={data.scope === 'lang'} class:on={data.scope === 'lang'} onclick={() => setScope('lang')}>{ta ? `எல்லா ${data.primary.language_ta ?? data.primary.language_native ?? data.primary.lang}` : `All ${data.primary.language ?? data.primary.lang}`}</button>
		<button type="button" role="radio" aria-checked={data.scope === 'all'} class:on={data.scope === 'all'} onclick={() => setScope('all')}>{ta ? 'எல்லாம்' : 'All versions'}</button>
	</div>

	<div class="within">
		<label>
			<span lang={ta ? 'ta' : 'en'}>{ta ? 'எதில்' : 'Within'}</span>
			<select value={data.range?.key ?? ''} onchange={(e) => setIn(e.currentTarget.value)} lang={ta ? 'ta' : 'en'}>
				<option value="">{ta ? 'முழு வேதாகமம்' : 'Whole Bible'}</option>
				<option value="ot">{ta ? 'பழைய ஏற்பாடு' : 'Old Testament'}</option>
				<option value="nt">{ta ? 'புதிய ஏற்பாடு' : 'New Testament'}</option>
				<optgroup label={ta ? 'பழைய ஏற்பாடு' : 'Old Testament'}>
					{#each otBooks as b (b.code)}<option value={b.slug}>{ta ? b.name_ta : b.name_en}</option>{/each}
				</optgroup>
				<optgroup label={ta ? 'புதிய ஏற்பாடு' : 'New Testament'}>
					{#each ntBooks as b (b.code)}<option value={b.slug}>{ta ? b.name_ta : b.name_en}</option>{/each}
				</optgroup>
			</select>
		</label>
		{#if data.range?.book}
			<form class="chapters" onsubmit={setChapters}>
				<span lang={ta ? 'ta' : 'en'}>{ta ? 'அதிகாரம்' : 'Chapters'}</span>
				<input type="number" inputmode="numeric" min="1" max={data.range.book.chapters} bind:value={chFrom} aria-label={ta ? 'முதல் அதிகாரம்' : 'From chapter'} placeholder="1" />
				<span aria-hidden="true">–</span>
				<input type="number" inputmode="numeric" min="1" max={data.range.book.chapters} bind:value={chTo} aria-label={ta ? 'கடைசி அதிகாரம்' : 'To chapter'} placeholder={String(data.range.book.chapters)} />
				<button type="submit" class="chip">{ta ? 'சரி' : 'Apply'}</button>
			</form>
		{/if}
	</div>

	{#if data.books?.length}
		<section class="books" aria-label={ta ? 'புத்தகங்கள்' : 'Books'}>
			<h2 class="kicker"><span lang="ta">புத்தகங்கள்</span> · Books</h2>
			<ul>
				{#each data.books as b (b.code)}
					<li>
						<a class="card book" href={chapterUrl(data.primary.code.toLowerCase(), b)}>
							<span class="ename" lang={ta ? 'ta' : 'en'}>{ta ? b.name_ta : b.name_en}</span>
							<span class="ealt" lang={ta ? 'en' : 'ta'}>{ta ? b.name_en : b.name_ta}<span class="ekind">{b.chapters} {ta ? 'அதிகாரங்கள்' : 'chapters'}</span></span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if data.words?.length}
		<section class="words" aria-label={ta ? 'எபிரெய, கிரேக்கச் சொற்கள்' : 'Hebrew and Greek words'}>
			<h2 class="kicker"><span lang="ta">மூலச்சொற்கள்</span> · Hebrew and Greek</h2>
			<ul>
				{#each data.words as w (w.id)}
					{@const he = w.id.startsWith('strongs/H')}
					<li>
						<a class="card word" href={w.href}>
							<span class="lemma" lang={he ? 'he' : 'el'} dir={he ? 'rtl' : 'ltr'}>{w.name}</span>
							<span class="ealt" lang="en">{w.alt} · {w.gloss}<span class="ekind">{w.n} {ta ? 'வசனங்கள்' : 'verses'}</span></span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if data.entities?.length}
		<section class="entities" aria-label={ta ? 'பெயர்களும் கட்டுரைகளும்' : 'Names and articles'}>
			<h2 class="kicker"><span lang="ta">பெயர்களும் கட்டுரைகளும்</span> · Names and articles</h2>
			<ul>
				{#each data.entities as e (e.id)}
					{@const label = entityLabelTa(e)}
					<li>
						<a class="card ent" href={entityHref(e)}>
							<span class="pin" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
								{#if e.type === 'place'}<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>
								{:else if e.type === 'person'}<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>
								{:else}<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 19a2.5 2.5 0 0 1 2.5-2.5H20"/>{/if}
							</svg></span>
							<span class="ename" lang={ta && label ? 'ta' : 'en'}>{ta && label ? label : e.name_en}</span>
							<span class="ealt" lang={ta ? 'en' : 'ta'}>{ta ? e.name_en : (label ?? '')}<span class="ekind" lang={ta ? 'ta' : 'en'}>{entityKind(e.type, ta ? 'ta' : 'en')}</span></span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if data.error}
		<p class="error" role="alert">{ta ? 'தேடல் தற்போது கிடைக்கவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும்.' : 'Search is unavailable right now. Please try again shortly.'}</p>
	{:else if !data.result}
		{#if data.common.length}
			<section class="common">
				<h2 class="kicker"><span lang="ta">அடிக்கடி தேடப்படுவை</span> · Common searches</h2>
				<ul>
					{#each data.common as c (c)}
						<li><a class="chip round" href={searchHref({ q: c })} lang={data.primary.lang}>{c}</a></li>
					{/each}
				</ul>
			</section>
		{/if}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'வசனக் குறிப்பை (எ.கா. யோவா 3:16) மேலே உள்ள பெட்டியில் தட்டச்சு செய்யவும். இங்கே சொற்களைத் தேடலாம்; சரியான சொற்றொடருக்கு மேற்கோள் குறிகள் இடுங்கள்.' : 'Type a reference such as John 3:16 in the box at the top. Here you can search words; put quotes around an exact phrase.'}</p>
	{:else}
		<p class="summary kicker" role="status">
			<span lang={ta ? 'ta' : 'en'}>{ta ? 'முடிவுகள்' : 'Results'}</span> · {data.result.total.toLocaleString()} {ta ? 'வசனங்கள்' : 'verses'}
			{#if data.widened}<span class="badge" lang={ta ? 'ta' : 'en'}>{ta ? `${data.primary.short}-இல் இல்லை · எல்லா பதிப்புகளிலும்` : `none in ${data.primary.short} · all versions`}</span>{/if}
			{#if data.result.exact}<span class="badge">{ta ? 'சரியான சொற்றொடர்' : 'exact phrase'}</span>{/if}
			{#if data.fromRoman}<span class="badge" lang="ta">{data.q} → {data.shown}</span>{/if}
			{#if data.range}<a class="badge range" href={searchHref({ range: null })} lang={ta ? 'ta' : 'en'} title={ta ? 'முழு வேதாகமத்திலும் தேடு' : 'Search the whole Bible'}>{rangeLabel(data.range, ta)} <span aria-hidden="true">✕</span></a>{/if}
			<span class="took">{data.result.took_ms} ms</span>
		</p>
		{#if data.fromRoman}
			<p class="roman" lang={ta ? 'ta' : 'en'}>
				{ta ? `“${data.q}” என்பதைத் தமிழில் “${data.shown}” எனத் தேடினோம்.` : `Searched “${data.q}” as Tamil: “${data.shown}”.`}
				<a href={`/search?${new URLSearchParams({ q: data.q, v: data.primary.code, scope: data.scope, lit: '1', ...rangeParams(data.range) })}`}>{ta ? `“${data.q}” என்றே தேடு` : `Search “${data.q}” as typed`}</a>
			</p>
		{:else if data.romanOffer}
			<p class="roman" lang={ta ? 'ta' : 'en'}>
				{ta ? 'தமிழ்ச் சொல்லா?' : 'Meant as Tamil?'}
				<a href={searchHref({ q: data.romanOffer })} lang="ta">{data.romanOffer}</a>
			</p>
		{/if}
		{#if groups.length}
			<nav class="bookjump" aria-label={ta ? 'புத்தகங்கள்' : 'Books'}>
				{#each groups as [ord, hits] (ord)}
					{@const book = findBook(hits[0].verse_id.split('.')[0])!}
					<a href="#b{ord}" lang={data.primary.lang}>{bookNameIn(book, data.primary)} <span class="n">{hits.length}</span></a>
				{/each}
			</nav>
		{/if}
		{#each groups as [ord, hits] (ord)}
			{@const book = findBook(hits[0].verse_id.split('.')[0])!}
			<section class="group" id="b{ord}">
				<h2 lang={data.primary.lang}>
					{bookNameIn(book, data.primary)}
					{#if !data.range?.book}<a class="only" href={searchHref({ range: { key: book.slug, book, bookMin: book.order, bookMax: book.order } })} lang={ta ? 'ta' : 'en'}>{ta ? 'இதில் மட்டும் தேடு' : 'Search only here'}</a>{/if}
				</h2>
				<ol>
					{#each hits as hit (hit.version + hit.verse_id)}
						{@const r = refOf(hit)}
						<li lang={r.lang}>
							<a class="ref" href={r.href}>{r.label}{#if data.versions.length > 1} <span class="v">{r.short}</span>{/if}</a>
							<p>{#each mark(hit.text) as run, i (i)}{#if run.hit}<mark>{run.t}</mark>{:else}{run.t}{/if}{/each}</p>
						</li>
					{/each}
				</ol>
			</section>
		{/each}
		{#if data.result.total > data.offset + pageSize}
			<a class="chip more" href={searchHref({ offset: data.offset + pageSize })}>{ta ? 'மேலும்' : 'More'} ›</a>
		{/if}
	{/if}
</div>

<style>
	.search { max-width: 44rem; }
	h1 { font-size: 1.8rem; font-weight: 600; margin: 0 0 1rem; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.searchform { display: flex; gap: 0.6rem; }
	.box { position: relative; flex: 1; }
	.icon { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: var(--accent); pointer-events: none; }
	.box input { min-height: 52px; padding-left: 2.7rem; border-color: var(--accent); font-size: 1.05rem; }
	.box input::-webkit-search-cancel-button { -webkit-appearance: none; }
	.searchform .chip { min-height: 52px; border-radius: var(--r-l); padding: 0 1.2rem; }
	.scope { display: inline-flex; gap: 0.3rem; margin: 1rem 0 1.4rem; background: var(--surface-3); border-radius: 14px; padding: 4px; }
	.scope button { padding: 0.5rem 0.9rem; border: 0; border-radius: 10px; background: transparent; color: var(--muted); cursor: pointer; font-family: var(--tamil); font-weight: 600; min-height: 42px; }
	.scope button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.within { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem 1.2rem; margin: -0.6rem 0 1.4rem; font-size: 0.9rem; color: var(--muted); }
	.within label, .within .chapters { display: inline-flex; align-items: center; gap: 0.5rem; }
	.within [lang='ta'] { font-family: var(--tamil); }
	.within select { min-height: 42px; max-width: 16rem; padding: 0.3rem 0.6rem; border: var(--bw) solid var(--line); border-radius: var(--r-s); background: var(--surface); color: var(--ink); font: inherit; }
	.within select[lang='ta'] { font-family: var(--tamil); }
	.within input { width: 4.2rem; min-height: 42px; padding: 0.3rem 0.5rem; }
	.within .chip { min-height: 42px; }
	.roman { margin: -0.3rem 0 1rem; font-size: 0.9rem; color: var(--muted); }
	.roman[lang='ta'], .roman a[lang='ta'] { font-family: var(--tamil); }
	.roman a { margin-left: 0.4rem; font-weight: 600; }
	.badge.range { color: var(--accent); border-color: var(--accent); text-decoration: none; }
	.group h2 .only { margin-left: 0.6rem; font-size: 0.75rem; font-weight: 600; letter-spacing: 0; text-transform: none; }
	.group h2 .only[lang='ta'] { font-family: var(--tamil); }
	.summary { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; margin: 0 0 0.8rem; }
	.summary [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.badge { font-size: 0.7rem; border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 0.1rem 0.6rem; text-transform: none; letter-spacing: 0; font-weight: 600; }
	.took { margin-left: auto; font-weight: 500; letter-spacing: 0; text-transform: none; }
	.bookjump { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; margin: 0 0 1.2rem; font-size: 0.9rem; font-weight: 600; }
	.bookjump a { text-decoration: none; }
	.bookjump a[lang='ta'] { font-family: var(--tamil); }
	.bookjump .n { color: var(--muted); font-size: 0.8em; font-weight: 500; }
	.group { margin-bottom: 1.6rem; }
	.group h2 { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin: 1.2rem 0 0.5rem; color: var(--muted); }
	.group h2[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; text-transform: none; font-size: 0.9rem; }
	.group ol { list-style: none; padding: 0; margin: 0; }
	.group li { padding: 0.9rem 0; border-bottom: var(--bw) solid var(--line); }
	.group li[lang='ta'] p { font-family: var(--tamil); font-size: 1.2rem; line-height: 1.8; }
	.group li[lang='en'] p { font-family: var(--en); font-size: 1.06rem; line-height: 1.75; color: var(--ink-en); }
	.group p { margin: 0.35rem 0 0; text-wrap: pretty; }
	.ref { font-weight: 700; text-decoration: none; font-size: 0.92rem; }
	li[lang='ta'] .ref { font-family: var(--tamil); }
	.ref .v { font-weight: 500; color: var(--muted); font-size: 0.8em; margin-left: 0.3rem; }
	mark { background: var(--hl); color: inherit; font-weight: 600; border-radius: 2px; padding: 0 0.05em; }
	.more { margin-top: 1rem; }
	.common h2 { margin: 0.5rem 0 0.7rem; }
	.common h2 [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.common ul { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.common .chip { font-weight: 500; color: var(--ink-2); min-height: 40px; }
	.common .chip[lang='ta'] { font-family: var(--tamil); }
	.entities { margin: 0 0 1.4rem; }
	.entities h2 { margin: 0 0 0.6rem; }
	.entities h2 [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.words ul { list-style: none; margin: 0 0 1.4rem; padding: 0; display: grid; gap: 0.6rem; grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr)); }
	.card.word { display: grid; gap: 0.15rem; padding: 0.7rem 0.9rem; border: var(--bw) solid var(--line-2); border-radius: var(--r-l); background: var(--surface); text-decoration: none; color: inherit; }
	.card.word:hover { border-color: var(--accent); }
	.lemma { font-size: 1.35rem; line-height: 1.3; }
	.books ul { list-style: none; margin: 0 0 1.4rem; padding: 0; display: grid; gap: 0.6rem; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr)); }
	.card.book { display: grid; gap: 0.15rem; padding: 0.7rem 0.9rem; border: var(--bw) solid var(--line-2); border-radius: var(--r-l); background: var(--surface); text-decoration: none; color: inherit; }
	.card.book:hover { border-color: var(--accent); }
	.entities ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr)); gap: 0.6rem; }
	.ent { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; column-gap: 0.6rem; align-items: baseline; padding: 0.7rem 0.9rem; text-decoration: none; color: inherit; border-radius: 14px; }
	.ent:hover { border-color: var(--accent); }
	.ent .pin { grid-row: 1 / span 2; color: var(--accent); align-self: center; }
	.ename { font-weight: 700; font-size: 1.05rem; }
	.ename[lang='ta'] { font-family: var(--tamil); }
	.ealt { font-size: 0.78rem; color: var(--muted); }
	.ealt[lang='ta'] { font-family: var(--tamil); }
	.ekind { margin-left: 0.5rem; font-size: 0.7rem; border: 1px solid var(--line); border-radius: 999px; padding: 0 0.45rem; }
	.ekind[lang='ta'] { font-family: var(--tamil); }
	.hint { color: var(--muted); max-width: 42rem; margin-top: 1.5rem; line-height: 1.7; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.error { color: var(--amber); }
</style>

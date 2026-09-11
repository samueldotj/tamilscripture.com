<script lang="ts">
	import { goto } from '$app/navigation';
	import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
	import { queryTokens } from '$lib/search/api';
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	let q = $state('');
	$effect(() => { q = data.q; });

	function submit(e: Event) {
		e.preventDefault();
		if (q.trim().length < 2) return;
		goto(`/search?${new URLSearchParams({ q: q.trim(), v: data.primary.code, scope: data.scope })}`);
	}
	function setScope(scope: string) {
		goto(`/search?${new URLSearchParams({ q: data.q, v: data.primary.code, scope })}`);
	}

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
	const tokens = $derived(queryTokens(data.q));

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
			label: `${version.lang === 'ta' ? book.name_ta : book.name_en} ${ch}:${v}`,
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
		<button type="button" role="radio" aria-checked={data.scope === 'lang'} class:on={data.scope === 'lang'} onclick={() => setScope('lang')}>{data.primary.lang === 'ta' ? (ta ? 'எல்லா தமிழ்' : 'All Tamil') : (ta ? 'எல்லா ஆங்கிலம்' : 'All English')}</button>
		<button type="button" role="radio" aria-checked={data.scope === 'all'} class:on={data.scope === 'all'} onclick={() => setScope('all')}>{ta ? 'எல்லாம்' : 'All versions'}</button>
	</div>

	{#if data.error}
		<p class="error" role="alert">{ta ? 'தேடல் தற்போது கிடைக்கவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும்.' : 'Search is unavailable right now. Please try again shortly.'}</p>
	{:else if !data.result}
		{#if data.common.length}
			<section class="common">
				<h2 class="kicker"><span lang="ta">அடிக்கடி தேடப்படுவை</span> · Common searches</h2>
				<ul>
					{#each data.common as c (c)}
						<li><a class="chip round" href={`/search?${new URLSearchParams({ q: c, v: data.primary.code })}`} lang={data.primary.lang}>{c}</a></li>
					{/each}
				</ul>
			</section>
		{/if}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'வசனக் குறிப்பை (எ.கா. யோவா 3:16) மேலே உள்ள பெட்டியில் தட்டச்சு செய்யவும். இங்கே சொற்களைத் தேடலாம்; சரியான சொற்றொடருக்கு மேற்கோள் குறிகள் இடுங்கள்.' : 'Type a reference such as John 3:16 in the box at the top. Here you can search words; put quotes around an exact phrase.'}</p>
	{:else}
		<p class="summary kicker" role="status">
			<span lang={ta ? 'ta' : 'en'}>{ta ? 'முடிவுகள்' : 'Results'}</span> · {data.result.total.toLocaleString()} {ta ? 'வசனங்கள்' : 'verses'}
			{#if data.result.exact}<span class="badge">{ta ? 'சரியான சொற்றொடர்' : 'exact phrase'}</span>{/if}
			<span class="took">{data.result.took_ms} ms</span>
		</p>
		{#if groups.length}
			<nav class="bookjump" aria-label={ta ? 'புத்தகங்கள்' : 'Books'}>
				{#each groups as [ord, hits] (ord)}
					{@const book = findBook(hits[0].verse_id.split('.')[0])!}
					<a href="#b{ord}" lang={data.primary.lang}>{data.primary.lang === 'ta' ? book.name_ta : book.name_en} <span class="n">{hits.length}</span></a>
				{/each}
			</nav>
		{/if}
		{#each groups as [ord, hits] (ord)}
			{@const book = findBook(hits[0].verse_id.split('.')[0])!}
			<section class="group" id="b{ord}">
				<h2 lang={data.primary.lang}>{data.primary.lang === 'ta' ? book.name_ta : book.name_en}</h2>
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
			<a class="chip more" href={`/search?${new URLSearchParams({ q: data.q, v: data.primary.code, scope: data.scope, offset: String(data.offset + pageSize) })}`}>{ta ? 'மேலும்' : 'More'} ›</a>
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
	.hint { color: var(--muted); max-width: 42rem; margin-top: 1.5rem; line-height: 1.7; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.error { color: var(--amber); }
</style>

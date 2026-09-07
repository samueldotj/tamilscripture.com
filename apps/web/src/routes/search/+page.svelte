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

<h1>{ta ? 'தேடல்' : 'Search'}</h1>

<form class="searchform" role="search" onsubmit={submit}>
	<input type="search" bind:value={q} lang={data.primary.lang} placeholder={ta ? 'சொல் அல்லது "சொற்றொடர்"' : 'word or "exact phrase"'} aria-label={ta ? 'தேடு' : 'Search'} autocomplete="off" />
	<button type="submit">{ta ? 'தேடு' : 'Search'}</button>
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
			<h2>{ta ? 'அடிக்கடி தேடப்படுவை' : 'Common searches'}</h2>
			<ul>
				{#each data.common as c (c)}
					<li><a href={`/search?${new URLSearchParams({ q: c, v: data.primary.code })}`} lang={data.primary.lang}>{c}</a></li>
				{/each}
			</ul>
		</section>
	{/if}
	<p class="hint">{ta ? 'வசனக் குறிப்பை (எ.கா. யோவா 3:16) மேலே உள்ள பெட்டியில் தட்டச்சு செய்யவும். இங்கே சொற்களைத் தேடலாம்; சரியான சொற்றொடருக்கு மேற்கோள் குறிகள் இடுங்கள்.' : 'Type a reference such as John 3:16 in the box at the top. Here you can search words; put quotes around an exact phrase.'}</p>
{:else}
	<p class="summary" role="status">
		{data.result.total.toLocaleString()} {ta ? 'வசனங்கள்' : 'verses'}
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
		<a class="more" href={`/search?${new URLSearchParams({ q: data.q, v: data.primary.code, scope: data.scope, offset: String(data.offset + pageSize) })}`}>{ta ? 'மேலும்' : 'More'} ›</a>
	{/if}
{/if}

<style>
	h1 { font-family: var(--tamil); font-size: 1.6rem; margin: 0 0 1rem; }
	.searchform { display: flex; gap: 0.5rem; max-width: 40rem; }
	.searchform input { flex: 1; font: inherit; font-family: var(--tamil); padding: 0.6rem 0.8rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
	.searchform button { padding: 0.6rem 1.1rem; border: 0; border-radius: 6px; background: var(--accent); color: #fff; cursor: pointer; font-family: var(--tamil); }
	.scope { display: inline-flex; margin: 0.8rem 0 1.2rem; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
	.scope button { padding: 0.45rem 0.9rem; border: 0; background: var(--surface); color: inherit; cursor: pointer; font-family: var(--tamil); min-height: 40px; }
	.scope button + button { border-left: 1px solid var(--line); }
	.scope button.on { background: var(--accent); color: #fff; }
	.summary { color: var(--muted); display: flex; gap: 0.8rem; align-items: center; }
	.badge { font-size: 0.75rem; border: 1px solid var(--line); border-radius: 999px; padding: 0.1rem 0.6rem; }
	.took { font-size: 0.8rem; margin-left: auto; }
	.bookjump { display: flex; flex-wrap: wrap; gap: 0.4rem 0.9rem; margin: 0 0 1.2rem; font-size: 0.9rem; }
	.bookjump a { text-decoration: none; }
	.bookjump .n { color: var(--muted); font-size: 0.8em; }
	.group { max-width: 42rem; margin-bottom: 1.5rem; }
	.group h2 { font-size: 1rem; margin: 1rem 0 0.4rem; color: var(--muted); font-family: var(--tamil); }
	.group ol { list-style: none; padding: 0; margin: 0; }
	.group li { padding: 0.6rem 0; border-top: 1px solid var(--line); }
	.group li[lang='ta'] p { font-family: var(--tamil); line-height: 1.8; }
	.group li[lang='en'] p { font-family: var(--serif); }
	.group p { margin: 0.2rem 0 0; }
	.ref { font-weight: 600; text-decoration: none; font-family: var(--tamil); }
	.ref .v { font-weight: 400; color: var(--muted); font-size: 0.8em; margin-left: 0.3rem; }
	mark { background: var(--select); color: inherit; border-radius: 2px; padding: 0 0.1em; }
	.more { display: inline-block; margin-top: 1rem; }
	.common h2 { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
	.common ul { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.common a { display: inline-block; padding: 0.3rem 0.8rem; border: 1px solid var(--line); border-radius: 999px; text-decoration: none; font-family: var(--tamil); }
	.hint { color: var(--muted); max-width: 42rem; margin-top: 1.5rem; }
	.error { color: var(--accent); }
</style>

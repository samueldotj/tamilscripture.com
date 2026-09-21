<script lang="ts">
	// Design 7A, dictionary browse: one index across people, places, books and
	// dictionary articles, with a search box, type filters and a letter rail.
	import { settings } from '$lib/settings/store.svelte';
	import { SOURCES, SOURCE_ORDER } from '$lib/entities/sources';
	import type { BrowseRow, BrowseType } from '../api/dictionary/browse/+server';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');

	// The rail and rows come from the server; switching letter or filter fetches
	// the next slice rather than reloading the page.
	// svelte-ignore state_referenced_locally
	let letters = $state<string[]>(data.letters);
	// svelte-ignore state_referenced_locally
	let letter = $state(data.letter);
	// svelte-ignore state_referenced_locally
	let rows = $state<BrowseRow[]>(data.rows);
	// svelte-ignore state_referenced_locally
	let total = $state(data.total);
	// svelte-ignore state_referenced_locally
	let type = $state<BrowseType>(data.type);
	let loading = $state(false);
	let q = $state('');
	let hits = $state<BrowseRow[] | null>(null);
	let searching = $state(false);
	let seq = 0;
	let timer: ReturnType<typeof setTimeout> | undefined;

	const TYPES: { id: BrowseType; ta: string; en: string }[] = [
		{ id: 'all', ta: 'எல்லாம்', en: 'All' },
		{ id: 'people', ta: 'நபர்கள்', en: 'People' },
		{ id: 'places', ta: 'இடங்கள்', en: 'Places' },
		{ id: 'words', ta: 'சொற்கள்', en: 'Words' }
	];
	const kinds = { person: ['நபர்', 'person'], place: ['இடம்', 'place'], book: ['புத்தகம்', 'book'], article: ['அகராதி', 'dictionary'] } as const;

	async function browse(next: { letter?: string; type?: BrowseType } = {}) {
		const nextType = next.type ?? type;
		const nextLetter = next.type && next.type !== type ? '' : (next.letter ?? letter);
		loading = true;
		const mine = ++seq;
		try {
			const res = await fetch(`/api/dictionary/browse?${new URLSearchParams({ t: nextType, l: nextLetter, lang: ta ? 'ta' : 'en', s: data.source })}`);
			if (!res.ok || mine !== seq) return;
			const d = (await res.json()) as { letters: string[]; letter: string; rows: BrowseRow[]; total: number };
			letters = d.letters;
			letter = d.letter;
			rows = d.rows;
			total = d.total;
			type = nextType;
			const u = new URL(location.href);
			u.searchParams.set('t', nextType);
			u.searchParams.set('l', d.letter);
			history.replaceState(null, '', u);
		} finally {
			if (mine === seq) loading = false;
		}
	}

	// The interface language decides which script the index is filed under.
	// svelte-ignore state_referenced_locally
	let lastLang = data.lang;
	$effect(() => {
		const now = ta ? 'ta' : 'en';
		if (now !== lastLang) {
			lastLang = now;
			void browse({ letter: '' });
		}
	});

	function onSearch() {
		const text = q.trim();
		clearTimeout(timer);
		if (text.length < 2) {
			hits = null;
			searching = false;
			return;
		}
		searching = true;
		const mine = ++seq;
		timer = setTimeout(async () => {
			const res = await fetch(`/api/dictionary/browse?${new URLSearchParams({ t: type, q: text, lang: ta ? 'ta' : 'en', s: data.source })}`).catch(() => null);
			const found = res?.ok ? ((await res.json()).rows as BrowseRow[]) : [];
			if (mine === seq) {
				hits = found;
				searching = false;
			}
		}, 180);
	}

	const totalText = $derived(total.toLocaleString('en-IN'));
</script>

<svelte:head>
	<title>{ta ? 'வேதாகம அகராதி' : 'Bible Dictionary'} · Tamil Scripture</title>
	<meta
		name="description"
		content={ta
			? `வேதாகம அகராதி: நபர்கள், இடங்கள், புத்தகங்கள் மற்றும் Aquifer, ஈஸ்டன், ஸ்மித் அகராதிக் கட்டுரைகள் ஒரே அகர வரிசையில்.`
			: `Bible dictionary: people, places, books and articles from the Aquifer Open Bible Dictionary, Easton’s and Smith’s in one alphabetical index.`}
	/>
	<link rel="canonical" href="https://www.tamilscripture.com/dictionary" />
</svelte:head>

{#snippet row(r: BrowseRow)}
					<a class="row" href={r.href}>
						<span class="text">
							<span class="name" lang={/[a-z]/i.test(r.name[0]) ? 'en' : 'ta'}>{r.name}</span>
							<span class="meta" lang={ta ? 'ta' : 'en'}>
								{#if r.alt}<span class="alt" lang={/[a-z]/i.test(r.alt[0]) ? 'en' : 'ta'}>{r.alt}&nbsp;·&nbsp;</span>{/if}<span>{ta ? kinds[r.type][0] : kinds[r.type][1]}</span>{#if r.gloss}<span class="gloss" lang={r.type === 'person' || r.type === 'place' ? 'en' : undefined}>&nbsp;·&nbsp;{r.gloss}</span>{/if}
							</span>
						</span>
						{#if r.n && (r.type === 'person' || r.type === 'place')}<span class="n" title={ta ? 'வசனங்கள்' : 'verses'}>{r.n.toLocaleString('en-IN')}</span>{/if}
						<span class="go" aria-hidden="true">›</span>
					</a>
{/snippet}

<article class="dict">
	<header class="head">
		<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'அகராதி' : 'Dictionary'}</h1>
		<p class="sub" lang={ta ? 'ta' : 'en'}>{ta ? 'வேதாகம அகராதி' : 'Bible dictionary'} · {totalText} {ta ? 'பதிவுகள்' : 'entries'}</p>

		<div class="box">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5 20 20" /></svg>
			<input type="search" bind:value={q} oninput={onSearch} placeholder={ta ? 'சொல் தேடு · search a word' : 'search a word'} aria-label={ta ? 'சொல் தேடு' : 'Search a word'} autocomplete="off" />
		</div>

		<div class="types" role="group" aria-label={ta ? 'வகை' : 'Type'}>
			{#each TYPES as t (t.id)}
				<button type="button" class:on={type === t.id} onclick={() => browse({ type: t.id })} lang={ta ? 'ta' : 'en'}>{ta ? t.ta : t.en}</button>
			{/each}
		</div>
	</header>

	<div class="body">
		<div class="list" aria-busy={loading}>
			{#if hits}
				{#if searching && !hits.length}
					<p class="muted">…</p>
				{:else if !hits.length}
					<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'பொருந்தும் பதிவுகள் இல்லை.' : 'Nothing matches.'}</p>
				{:else}
					{#each hits as r (r.id)}
						{@render row(r)}
					{/each}
				{/if}
			{:else if !rows.length}
				<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த எழுத்தில் பதிவுகள் இல்லை.' : 'Nothing under this letter.'}</p>
			{:else}
				<h2 class="letter" lang={ta ? 'ta' : 'en'} aria-live="polite">{letter}</h2>
				{#each rows as r (r.id)}
					{@render row(r)}
				{/each}
			{/if}
		</div>

		{#if !hits}
			<nav class="rail" aria-label={ta ? 'எழுத்து' : 'Letter'}>
				{#each letters as l (l)}
					<button type="button" class:on={l === letter} aria-current={l === letter ? 'true' : undefined} onclick={() => browse({ letter: l })}>{l}</button>
				{/each}
			</nav>
		{/if}
	</div>

	<footer class="credits">
		{#each SOURCE_ORDER.filter((k) => SOURCES[k]) as k (k)}
			<p><a href={SOURCES[k].url}>{SOURCES[k].name}</a> ({SOURCES[k].year}) · {ta ? SOURCES[k].licence_ta : SOURCES[k].licence_en}</p>
		{/each}
		<p lang={ta ? 'ta' : 'en'}>{ta ? 'நபர்கள்: STEP Bible TIPNR · CC BY 4.0. இடங்கள்: OpenBible.info · CC BY 4.0.' : 'People: STEP Bible TIPNR, CC BY 4.0. Places: OpenBible.info, CC BY 4.0.'}</p>
	</footer>
</article>

<style>
	.dict { max-width: 52rem; }
	.head { display: grid; gap: 0.5rem; margin-bottom: 1.1rem; }
	h1 { font-size: 2rem; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.sub { margin: 0; color: var(--muted); font-size: 0.9rem; }
	.sub[lang='ta'] { font-family: var(--tamil); }
	.box { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.5rem; padding: 0 0.9rem; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: 14px; color: var(--muted); }
	.box input { flex: 1; min-width: 0; font: inherit; font-size: 1rem; background: none; border: 0; padding: 0.85rem 0; color: var(--ink); font-family: var(--tamil); }
	.box input:focus { outline: none; }
	.box:focus-within { border-color: var(--accent); }
	.types { display: inline-flex; flex-wrap: wrap; gap: 0.25rem; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.types button { border: 0; border-radius: 9px; padding: 0.4rem 0.9rem; background: transparent; color: var(--muted); font: inherit; font-size: 0.85rem; font-weight: 600; cursor: pointer; min-height: 36px; }
	.types button[lang='ta'] { font-family: var(--tamil); }
	.types button.on { background: var(--accent); color: var(--on-accent); }

	.body { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0.8rem; align-items: start; }
	.list { display: grid; gap: 0.35rem; min-width: 0; }
	.list[aria-busy='true'] { opacity: 0.55; }
	.letter { margin: 0.2rem 0 0.1rem; font-size: 1.5rem; font-weight: 700; color: var(--accent); }
	.letter[lang='ta'] { font-family: var(--tamil); }
	.row { display: flex; align-items: center; gap: 0.8rem; padding: 0.7rem 0.9rem; border: var(--bw) solid var(--line); border-radius: var(--r-l); background: var(--surface); text-decoration: none; color: inherit; }
	.row:hover { border-color: var(--accent); }
	.text { display: grid; gap: 0.1rem; min-width: 0; flex: 1; }
	.name { font-size: 1.05rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.name[lang='ta'] { font-family: var(--tamil); font-size: 1.15rem; }
	.meta { font-size: 0.78rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.meta[lang='ta'] { font-family: var(--tamil); }
	.meta .alt[lang='en'], .meta .gloss[lang='en'] { font-family: var(--sans); }
	.n { font-size: 0.72rem; color: var(--muted); font-variant-numeric: tabular-nums; flex: none; }
	.go { color: var(--muted); flex: none; }

	.rail { position: sticky; top: calc(var(--header-h, 4.4rem) + 0.75rem); display: flex; flex-direction: column; gap: 1px; max-height: calc(100vh - var(--header-h, 4.4rem) - 3rem); overflow-y: auto; scrollbar-width: none; }
	.rail button { border: 0; background: none; color: var(--muted); font: inherit; font-size: 0.8rem; font-family: var(--tamil); line-height: 1.1; padding: 0.15rem 0.35rem; border-radius: 6px; cursor: pointer; }
	.rail button:hover { color: var(--ink); background: var(--surface-2); }
	.rail button.on { background: var(--accent); color: var(--on-accent); font-weight: 700; }

	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.credits { margin-top: 1.6rem; display: grid; gap: 0.3rem; font-size: 0.75rem; color: var(--muted); }
	.credits p { margin: 0; }
	.credits a { color: inherit; }
	.credits [lang='ta'] { font-family: var(--tamil); }

	@media (max-width: 640px) {
		.row { padding: 0.65rem 0.75rem; }
		.rail button { padding: 0.1rem 0.25rem; }
	}
</style>

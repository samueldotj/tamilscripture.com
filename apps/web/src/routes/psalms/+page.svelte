<script lang="ts">
	// Psalms explorer (Claude Design handoff, Psalms Explorer v2 and Psalms Mobile
	// Screen; docs/feature_psalms_explorer.md): filter the 150 psalms by theme,
	// genre and author, and open one as a card. The selection lives in the
	// query string, replaced in place so Back leaves the page.
	import { untrack } from 'svelte';
	import { flip } from 'svelte/animate';
	import { scale } from 'svelte/transition';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { settings } from '$lib/settings/store.svelte';
	import { ANONYMOUS, EMPTY, count, fromQuery, isEmpty, matcher, toQuery, toggled, type Selection } from '$lib/psalms/filter';
	import { psalmOf } from '$lib/psalms/types';
	import PsalmCard from '$lib/psalms/PsalmCard.svelte';

	let { data } = $props();
	const index = $derived(data.index);
	const ta = $derived(settings.value.uiLang === 'ta');
	const psalms = $derived(index.psalms.map(psalmOf));
	const themeOf = $derived(new Map(index.themes.map((t) => [t.id, t])));

	// The URL seeds the selection once; after that the page writes the URL.
	const initial = untrack(() => fromQuery(data.index, page.url.searchParams));
	let sel = $state<Selection>(initial.selection);
	let open = $state(initial.psalm);
	let sheet = $state<HTMLDialogElement>();
	let cardEl = $state<HTMLElement>();

	const matches = $derived(matcher(index, sel));
	const shown = $derived(isEmpty(sel) ? psalms : psalms.filter(matches));
	const current = $derived(psalms[open - 1]);
	const reduced = browser && matchMedia('(prefers-reduced-motion: reduce)').matches;

	/** Writes the selection into the URL. Called from clicks only: on a direct load an
	 *  effect would run before the router starts, and replaceState would throw. */
	function syncUrl() {
		const q = toQuery(sel, open);
		if (page.url.search !== `?${q}`) replaceState(`?${q}`, page.state);
	}

	/** Change one facet; when the open psalm no longer matches, open the first that does. */
	function set(next: Selection) {
		sel = next;
		const ok = matcher(index, next);
		if (!ok(psalms[open - 1])) open = psalms.find(ok)?.n ?? open;
		syncUrl();
	}
	function pick(n: number) {
		open = n;
		syncUrl();
		if (matchMedia('(max-width: 52rem)').matches) cardEl?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
	}

	/** [primary, secondary] in the interface language's order. */
	const two = (t: string, e: string): [string, string] => (ta ? [t, e] : [e, t]);
	const themeCounts = $derived(new Map(index.themes.map((t) => [t.id, psalms.filter((p) => p.theme === t.id).length])));
	const anonymous = { id: ANONYMOUS, ta: 'அநாமதேய', en: 'Anonymous' };
	const authors = $derived([...index.authors, anonymous]);

	const names = $derived.by(() => {
		const facets = [
			...sel.genres.map((id) => index.genres.find((g) => g.id === id) ?? index.collections.find((c) => c.id === id)!),
			...sel.authors.map((id) => authors.find((a) => a.id === id)!)
		];
		const themes = sel.themes.map((id) => themeOf.get(id)!);
		return { facets, themes };
	});
	const gridTitle = $derived.by(() => {
		const { facets, themes } = names;
		const join = (xs: { ta: string; en: string }[], k: 'ta' | 'en') => xs.map((x) => x[k]).join(', ');
		if (!facets.length && !themes.length) return two('எல்லா சங்கீதங்களும்', 'All 150 psalms');
		const parts = (k: 'ta' | 'en') => [join(facets, k), join(themes, k)].filter(Boolean).join(' · ');
		if (!facets.length) return two(parts('ta'), `Psalms of ${join(themes, 'en').toLowerCase()}`);
		return two(parts('ta'), parts('en'));
	});
	const caption = $derived(
		isEmpty(sel)
			? ta ? '150 சங்கீதங்கள் · ஒவ்வொரு எண்ணின் கீழுள்ள கோடு அதன் கருப்பொருள்' : '150 psalms · the bar beneath each number is its theme'
			: ta ? `150-இல் ${shown.length} · எண்ணைத் தொட்டுத் திறக்கவும்` : `${shown.length} of 150${sel.themes.length && count(sel) > sel.themes.length ? ' · matching every filter' : ''} · tap a number to open it`
	);
	const showLabel = $derived(ta ? `${shown.length} சங்கீதங்களைக் காட்டு` : `Show ${shown.length} psalm${shown.length === 1 ? '' : 's'}`);
</script>

<svelte:head>
	<title>{ta ? 'சங்கீதங்களை ஆராயுங்கள்' : 'Psalms explorer'} · {ta ? 'தமிழ் வேதாகமம்' : 'Tamil Scripture'}</title>
	<meta name="description" content="Explore the 150 Psalms by theme, genre and author, each with a short summary and a key verse in Tamil and English." />
	<link rel="canonical" href="https://www.tamilscripture.com/psalms" />
</svelte:head>

{#snippet chip(label: { ta: string; en: string }, on: boolean, onclick: () => void, wide = false)}
	{@const [a, b] = two(label.ta, label.en)}
	<button type="button" class="chip" class:wide class:on aria-pressed={on} {onclick}>
		<span class="a" lang={ta ? 'ta' : 'en'}>{a}</span>
		<span class="b" lang={ta ? 'en' : 'ta'}>{b}</span>
	</button>
{/snippet}

{#snippet heading(t: string, e: string, extra?: () => void)}
	{@const [a, b] = two(t, e)}
	<div class="h-row">
		<h2><span lang={ta ? 'ta' : 'en'}>{a}</span><span class="sub" lang={ta ? 'en' : 'ta'}>{b}</span></h2>
		{#if extra}<button type="button" class="clear" onclick={extra}>{ta ? 'தேர்வை நீக்கு' : 'Clear selection'}</button>{/if}
	</div>
{/snippet}

{#snippet genrePanel(clearable: boolean)}
	<section>
		{@render heading('வகை', 'Genre', clearable && !isEmpty(sel) ? () => set(EMPTY) : undefined)}
		<div class="col">
			{#each index.genres as g (g.id)}
				{@render chip(g, sel.genres.includes(g.id), () => set({ ...sel, genres: toggled(sel.genres, g.id) }), true)}
			{/each}
			<span class="sep" aria-hidden="true"></span>
			{#each index.collections as c (c.id)}
				{@render chip(c, sel.genres.includes(c.id), () => set({ ...sel, genres: toggled(sel.genres, c.id) }), true)}
			{/each}
		</div>
	</section>
{/snippet}

{#snippet themeTiles()}
	<div class="themes">
		{#each index.themes as t (t.id)}
			{@const on = sel.themes.includes(t.id)}
			{@const [a, b] = two(t.ta, t.en)}
			<button type="button" class="theme" class:on class:dim={sel.themes.length && !on} aria-pressed={on} style="--tc: {t.color}" onclick={() => set({ ...sel, themes: toggled(sel.themes, t.id) })}>
				<span class="a" lang={ta ? 'ta' : 'en'}>{a}</span>
				<span class="b">{b} · {themeCounts.get(t.id)}</span>
			</button>
		{/each}
	</div>
{/snippet}

{#snippet authorRow()}
	<section>
		{@render heading('ஆசிரியர்', 'Author')}
		<div class="row">
			{#each authors as a (a.id)}
				{@render chip(a, sel.authors.includes(a.id), () => set({ ...sel, authors: toggled(sel.authors, a.id) }))}
			{/each}
		</div>
	</section>
{/snippet}

<section class="intro">
	<span class="kicker">{ta ? 'சங்கீதங்கள் · 150 பாடல்கள்' : 'Psalms · 150 songs'}</span>
	<h1 lang="ta">சங்கீதங்களைக் கருப்பொருள் வாரியாக ஆராயுங்கள்</h1>
	<p>Explore the Psalms by theme. Filter by genre or author, browse the eight themes, or open any of the 150 from the grid, each with a short summary and a key verse in Tamil and English.</p>
</section>

<div class="layout">
	<aside class="side wide-only">
		{@render genrePanel(true)}
	</aside>

	<div class="main">
		<div class="wide-only mid-only stack">
			{@render authorRow()}
		</div>

		<section class="themes-mid">
			<div class="h-row">
				<h2><span lang={ta ? 'ta' : 'en'}>{ta ? 'கருப்பொருள்கள்' : 'Themes'}</span><span class="sub" lang={ta ? 'en' : 'ta'}>{ta ? 'Themes' : 'கருப்பொருள்கள்'}</span></h2>
				<button type="button" class="filters narrow-only" aria-label={ta ? 'வடிகட்டிகள்' : 'Filters'} onclick={() => sheet?.showModal()}>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4" /></svg>
					{ta ? 'வடிகட்டு' : 'Filters'}
					{#if count(sel) - sel.themes.length}<span class="badge">{count(sel) - sel.themes.length}</span>{/if}
				</button>
			</div>
			{@render themeTiles()}
		</section>

		<section>
			<div class="h-row">
				<h2><span lang={ta ? 'ta' : 'en'}>{gridTitle[0]}</span><span class="sub" lang={ta ? 'en' : 'ta'}>{gridTitle[1]}</span></h2>
				<span class="caption">{caption}</span>
			</div>
			<div class="grid">
				{#each shown as p (p.n)}
					{@const t = themeOf.get(p.theme)!}
					<button type="button" class="cell" class:on={p.n === open} aria-pressed={p.n === open} title="{ta ? 'சங்கீதம்' : 'Psalm'} {p.n} · {ta ? t.ta : t.en}" style="--tc: {t.color}" onclick={() => pick(p.n)}
						animate:flip={{ duration: reduced ? 0 : 320 }} in:scale={{ duration: reduced ? 0 : 280, delay: reduced ? 0 : 120, start: 0.6 }}>{p.n}</button>
				{/each}
			</div>
			<div class="legend">
				{#each index.themes as t (t.id)}
					<span><i style="--tc: {t.color}"></i>{ta ? t.ta : t.en}</span>
				{/each}
			</div>
		</section>

		<div bind:this={cardEl} class="card-anchor">
			{#key open}
				<PsalmCard {index} psalm={current} onpick={pick} {ta} />
			{/key}
		</div>
	</div>

	<!-- Large screens: author and themes in a column of their own, right of the grid. -->
	<aside class="right large-only">
		<div class="stack">
			{@render authorRow()}
		</div>
		<section>
			<div class="h-row">
				<h2><span lang={ta ? 'ta' : 'en'}>{ta ? 'கருப்பொருள்கள்' : 'Themes'}</span><span class="sub" lang={ta ? 'en' : 'ta'}>{ta ? 'Themes' : 'கருப்பொருள்கள்'}</span></h2>
			</div>
			{@render themeTiles()}
		</section>
	</aside>
</div>

<dialog bind:this={sheet} class="sheet" aria-label={ta ? 'வடிகட்டிகள்' : 'Filters'} onclick={(e) => { if (e.target === sheet) sheet?.close(); }}>
	<div class="sheet-head">
		<h2><span lang={ta ? 'ta' : 'en'}>{ta ? 'வடிகட்டு' : 'Filters'}</span></h2>
		{#if count(sel) - sel.themes.length}<button type="button" class="clear" onclick={() => set({ ...EMPTY, themes: sel.themes })}>{ta ? 'அனைத்தையும் நீக்கு' : 'Clear all'}</button>{/if}
		<button type="button" class="x" aria-label={ta ? 'மூடு' : 'Close'} onclick={() => sheet?.close()}>×</button>
	</div>
	<div class="sheet-body">
		{@render genrePanel(false)}
		{@render authorRow()}
	</div>
	<div class="sheet-foot"><button type="button" class="primary" onclick={() => sheet?.close()}>{showLabel}</button></div>
</dialog>

<style>
	.intro { margin: 0.5rem 0 2rem; }
	.kicker { display: block; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.4rem; }
	h1 { font-family: var(--tamil); font-size: 2.2rem; font-weight: 600; margin: 0 0 0.4rem; letter-spacing: -0.01em; line-height: 1.2; text-wrap: balance; }
	.intro p { color: var(--ink-2); max-width: 40rem; margin: 0; font-size: 1.02rem; line-height: 1.65; }

	.layout { display: grid; grid-template-columns: minmax(14rem, 16rem) minmax(0, 1fr); gap: 2rem; align-items: start; }
	.side { position: sticky; top: calc(var(--header-h) + 1rem); max-height: calc(100vh - var(--header-h) - 2rem); overflow: auto; padding-right: 0.25rem; }
	.main, .stack { display: flex; flex-direction: column; gap: 2rem; min-width: 0; }
	.stack { gap: 1.6rem; }

	.h-row { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem 1rem; flex-wrap: wrap; margin-bottom: 0.7rem; }
	h2 { margin: 0; font-size: 1.15rem; font-weight: 600; color: var(--amber); display: flex; gap: 0.6rem; align-items: baseline; flex-wrap: wrap; }
	h2 [lang='ta'] { font-family: var(--tamil); }
	h2 .sub { font-size: 0.92rem; color: var(--muted); }
	.side h2 { font-size: 1.05rem; }
	.clear { border: 0; background: none; color: var(--accent); font-weight: 600; font-size: 0.9rem; cursor: pointer; padding: 0.3rem 0; text-decoration: underline; text-underline-offset: 3px; }
	.caption { font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums; }

	.col { display: flex; flex-direction: column; gap: 0.4rem; }
	.row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.sep { height: 1px; background: var(--line); margin: 0.4rem 0; }
	.chip { display: inline-flex; flex-direction: column; align-items: flex-start; min-height: 42px; padding: 0.45rem 0.9rem; border: var(--bw) solid var(--line-2); border-radius: 11px; background: var(--surface); color: var(--ink); cursor: pointer; text-align: left; line-height: 1.3; font: inherit; }
	.chip.wide { display: flex; width: 100%; }
	.chip:hover { border-color: var(--accent); }
	.chip .a { font-weight: 600; font-size: 1rem; white-space: nowrap; }
	.chip .a[lang='ta'] { font-family: var(--tamil); }
	.chip .b { font-size: 0.74rem; color: var(--muted); white-space: nowrap; }
	.chip .b[lang='ta'] { font-family: var(--tamil); }
	.chip.wide .a, .chip.wide .b { white-space: normal; }
	.chip.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.chip.on .b { color: var(--on-accent); opacity: 0.8; }

	/* Theme colours from the design; lifted towards white on dark grounds. */
	.theme, .cell, .legend i { --tcx: var(--tc); }
	@media (prefers-color-scheme: dark) { :global(:root:not([data-theme='light'])) :is(.theme, .cell, .legend i) { --tcx: color-mix(in oklab, var(--tc) 70%, white); } }
	:global(:root[data-theme='dark']) :is(.theme, .cell, .legend i) { --tcx: color-mix(in oklab, var(--tc) 70%, white); }

	.themes { display: grid; grid-template-columns: repeat(auto-fill, minmax(11.5rem, 1fr)); gap: 0.65rem; }
	.theme { position: relative; display: flex; flex-direction: column; justify-content: center; gap: 0.1rem; min-height: 4rem; padding: 0.8rem 1rem; border: var(--bw) solid var(--line); border-radius: 14px; background: var(--surface); color: var(--ink); cursor: pointer; text-align: left; font: inherit; }
	.theme::after { content: ''; position: absolute; left: 1rem; right: 1rem; bottom: 0; height: 3px; border-radius: 3px 3px 0 0; background: var(--tcx); }
	.theme:hover { border-color: var(--accent); }
	.theme.on { border-color: var(--accent); background: var(--accent-soft); }
	.theme.dim { opacity: 0.55; }
	.theme .a { font-size: 1.12rem; font-weight: 600; line-height: 1.3; }
	.theme .a[lang='ta'] { font-family: var(--tamil); }
	.theme .b { font-size: 0.76rem; color: var(--muted); }

	.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(3.1rem, 1fr)); gap: 0.4rem; }
	.cell { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; border: var(--bw) solid var(--line); border-bottom: 4px solid var(--tcx); border-radius: 8px; background: var(--surface); cursor: pointer; font: inherit; font-weight: 600; font-size: 0.95rem; font-variant-numeric: tabular-nums; color: var(--ink); padding: 0; min-height: 44px; transition: border-color 0.15s; }
	.cell:hover { border-color: var(--accent); border-bottom-color: var(--tcx); }
	.cell.on { border-color: var(--accent); border-bottom-color: var(--tcx); background: var(--accent-soft); }
	.legend { display: flex; flex-wrap: wrap; gap: 0.4rem 1.1rem; margin-top: 0.8rem; }
	.legend span { display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.78rem; color: var(--muted); }
	.legend i { width: 10px; height: 10px; border-radius: 999px; background: var(--tcx); }
	.card-anchor { scroll-margin-top: calc(var(--header-h) + 1rem); }

	.filters { position: relative; display: inline-flex; align-items: center; gap: 0.4rem; min-height: 40px; padding: 0 0.8rem; border: var(--bw) solid var(--line-2); border-radius: 11px; background: var(--surface); color: var(--ink); font: inherit; font-weight: 600; font-size: 0.9rem; cursor: pointer; }
	.badge { position: absolute; top: -6px; right: -6px; min-width: 20px; height: 20px; padding: 0 5px; border-radius: 999px; background: #EC3013; color: #FFFFFF; font-size: 0.7rem; font-weight: 700; display: flex; align-items: center; justify-content: center; font-variant-numeric: tabular-nums; }

	.sheet { width: 100%; max-width: 40rem; max-height: 85vh; margin: auto auto 0; padding: 0; border: 0; border-radius: 20px 20px 0 0; background: var(--bg); color: var(--ink); display: none; flex-direction: column; }
	.sheet[open] { display: flex; }
	.sheet::backdrop { background: var(--scrim); }
	.sheet-head { display: flex; align-items: center; gap: 1rem; padding: 1rem 1rem 0.6rem; border-bottom: var(--bw) solid var(--line); }
	.sheet-head h2 { flex: 1; }
	.x { width: 40px; height: 40px; border: 0; border-radius: 999px; background: var(--surface-2); color: var(--ink-2); font-size: 1.4rem; cursor: pointer; }
	.sheet-body { overflow: auto; padding: 1rem; display: flex; flex-direction: column; gap: 1.6rem; }
	.sheet-foot { padding: 10px 16px 24px; border-top: var(--bw) solid var(--line); }
	.primary { width: 100%; min-height: 48px; border: var(--bw) solid var(--accent); border-radius: 12px; background: var(--accent); color: var(--on-accent); font: inherit; font-weight: 600; font-size: 0.98rem; cursor: pointer; font-variant-numeric: tabular-nums; }

	.narrow-only { display: none; }
	.large-only { display: none; }
	/* Large screens: genre, the grid and card in a 74rem middle, and author and themes, side by side in the centre. */
	@media (min-width: 100rem) {
		.layout { grid-template-columns: minmax(14rem, 16rem) minmax(0, 74rem) minmax(16rem, 20rem); justify-content: center; }
		.large-only { display: flex; }
		.mid-only, .themes-mid { display: none; }
		.right { position: sticky; top: calc(var(--header-h) + 1rem); max-height: calc(100vh - var(--header-h) - 2rem); overflow: auto; flex-direction: column; gap: 2rem; padding-right: 0.25rem; }
		.right .themes { grid-template-columns: minmax(0, 1fr); gap: 0.5rem; }
	}
	@media (max-width: 52rem) {
		.layout { grid-template-columns: minmax(0, 1fr); }
		.wide-only { display: none; }
		.narrow-only { display: inline-flex; }
		h1 { font-size: 1.7rem; }
		.themes { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
		.theme { min-height: 3.4rem; padding: 0.6rem 0.8rem; }
		.grid { grid-template-columns: repeat(auto-fill, minmax(2.8rem, 1fr)); }
	}
	@media (prefers-reduced-motion: reduce) { .cell { transition: none; } }
</style>

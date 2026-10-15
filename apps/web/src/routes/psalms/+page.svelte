<script lang="ts">
	// Psalms explorer (Claude Design "Psalms Explorer Redesign", Oct 2026;
	// docs/feature_psalms_explorer.md §5): a map of the 150 psalms coloured by theme,
	// filtered by theme, genre, collection and author, beside the open psalm's reading
	// pane. The psalms keep their places on the map; filters fade the ones that do not
	// match. On a phone the psalm comes first, and the map opens as a sheet from the bar
	// at the foot. The selection lives in the query string, replaced in place so Back
	// leaves the page.
	import { untrack } from 'svelte';
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
	type Menu = 'genre' | 'collection' | 'author';
	let menu = $state<Menu | null>(null);
	let goto = $state('');

	const matches = $derived(matcher(index, sel));
	const shown = $derived(isEmpty(sel) ? psalms : psalms.filter(matches));
	const current = $derived(psalms[open - 1]);
	const reduced = browser && matchMedia('(prefers-reduced-motion: reduce)').matches;

	/** The psalms before and after the open one, among those the filters keep. */
	const steps = $derived.by(() => {
		const list = shown.some((p) => p.n === open) ? shown : psalms;
		const i = list.findIndex((p) => p.n === open);
		return { prev: list[(i - 1 + list.length) % list.length].n, next: list[(i + 1) % list.length].n };
	});

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
		if (sheet?.open) sheet.close();
		// Bring the psalm's top into view when it has scrolled away.
		const top = cardEl?.getBoundingClientRect().top ?? 0;
		if (top < 0 || top > innerHeight * 0.6) cardEl?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
	}
	function go(e: SubmitEvent) {
		e.preventDefault();
		const n = Number(goto.trim());
		if (Number.isInteger(n) && n >= 1 && n <= 150) {
			pick(n);
			goto = '';
		}
	}

	/** [primary, secondary] in the interface language's order. */
	const two = (t: string, e: string): [string, string] => (ta ? [t, e] : [e, t]);
	const themeCounts = $derived(new Map(index.themes.map((t) => [t.id, psalms.filter((p) => p.theme === t.id).length])));
	const anonymous = { id: ANONYMOUS, ta: 'அநாமதேய', en: 'Anonymous' };
	const authors = $derived([...index.authors, anonymous]);
	const collectionIds = $derived(new Set(index.collections.map((c) => c.id)));

	const MENUS: { id: Menu; ta: string; en: string }[] = [
		{ id: 'genre', ta: 'வகை', en: 'Genre' },
		{ id: 'collection', ta: 'தொகுப்பு', en: 'Collection' },
		{ id: 'author', ta: 'ஆசிரியர்', en: 'Author' }
	];
	const menuItems = $derived<Record<Menu, { id: string; ta: string; en: string }[]>>({ genre: index.genres, collection: index.collections, author: authors });
	/** How many of a menu's values are chosen. */
	function chosen(m: Menu): number {
		if (m === 'author') return sel.authors.length;
		return sel.genres.filter((id) => collectionIds.has(id) === (m === 'collection')).length;
	}
	function isOn(m: Menu, id: string): boolean {
		return m === 'author' ? sel.authors.includes(id) : sel.genres.includes(id);
	}
	function toggle(m: Menu, id: string) {
		set(m === 'author' ? { ...sel, authors: toggled(sel.authors, id) } : { ...sel, genres: toggled(sel.genres, id) });
	}

	const names = $derived.by(() => {
		const facets = [
			...sel.genres.map((id) => index.genres.find((g) => g.id === id) ?? index.collections.find((c) => c.id === id)!),
			...sel.authors.map((id) => authors.find((a) => a.id === id)!),
			...sel.themes.map((id) => themeOf.get(id)!)
		];
		return facets.map((x) => (ta ? x.ta : x.en)).join(', ');
	});
	const countLine = $derived(
		isEmpty(sel)
			? ta ? '150 சங்கீதங்கள் · நிறம் ஒவ்வொன்றின் கருப்பொருள்' : 'All 150 psalms · the colour is each psalm’s theme'
			: ta ? `150-இல் ${shown.length} · ${names}` : `${shown.length} of 150 · ${names}`
	);
	const showLabel = $derived(ta ? `சங்கீதம் ${open}-ஐத் திற` : `Open Psalm ${open}`);
</script>

<svelte:head>
	<title>{ta ? 'சங்கீதங்களை ஆராயுங்கள்' : 'Psalms explorer'} · {ta ? 'தமிழ் வேதாகமம்' : 'Tamil Scripture'}</title>
	<meta name="description" content="Explore the 150 Psalms by theme, genre and author, each with a short summary and C. H. Spurgeon's commentary from The Treasury of David." />
	<link rel="canonical" href="https://www.tamilscripture.com/psalms" />
</svelte:head>

{#snippet chip(label: { ta: string; en: string }, on: boolean, onclick: () => void)}
	{@const [a, b] = two(label.ta, label.en)}
	<button type="button" class="chip" class:on aria-pressed={on} {onclick}>
		<span class="a" lang={ta ? 'ta' : 'en'}>{a}</span>
		<span class="b" lang={ta ? 'en' : 'ta'}>{b}</span>
	</button>
{/snippet}

{#snippet map(where: 'side' | 'sheet')}
	<section class="block">
		<div class="h-row">
			<h2><span lang="ta">கருப்பொருள்</span><span class="sub" lang="en">Theme</span></h2>
			{#if !isEmpty(sel)}<button type="button" class="clear" onclick={() => set(EMPTY)}>{ta ? 'எல்லாம் நீக்கு' : 'Clear all'}</button>{/if}
		</div>
		<div class="themes">
			{#each index.themes as t (t.id)}
				{@const on = sel.themes.includes(t.id)}
				{@const [a, b] = two(t.ta, t.en)}
				<button type="button" class="theme" class:on class:dim={sel.themes.length && !on} aria-pressed={on} style="--tc: {t.color}" onclick={() => set({ ...sel, themes: toggled(sel.themes, t.id) })}>
					<i aria-hidden="true"></i>
					<span class="names"><span class="a" lang={ta ? 'ta' : 'en'}>{a}</span><span class="b" lang={ta ? 'en' : 'ta'}>{b}</span></span>
					<span class="n">{themeCounts.get(t.id)}</span>
				</button>
			{/each}
		</div>
	</section>

	<section class="block">
		<div class="menus">
			{#each MENUS as m (m.id)}
				{@const [a, b] = two(m.ta, m.en)}
				{@const k = chosen(m.id)}
				<button type="button" class="menu" class:set={k > 0} aria-expanded={menu === m.id} aria-controls="menu-{where}" onclick={() => (menu = menu === m.id ? null : m.id)}>
					<span class="a" lang={ta ? 'ta' : 'en'}>{a}</span>
					<span class="b" lang={ta ? 'en' : 'ta'}>{b}</span>
					{#if k}<span class="badge">{k}</span>{/if}
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
				</button>
			{/each}
		</div>
		{#if menu}
			<div class="panel" id="menu-{where}">
				{#each menuItems[menu] as x (x.id)}
					{@render chip(x, isOn(menu, x.id), () => toggle(menu!, x.id))}
				{/each}
			</div>
		{/if}
	</section>

	{@render grid(where)}
{/snippet}

<!-- The 150 psalms: under the filters, or in a column of its own on large screens. -->
{#snippet grid(where: 'side' | 'sheet' | 'right')}
	<section class="block" class:in-side={where === 'side'}>
		{#if where === 'right'}<h2><span lang="ta">150 சங்கீதங்கள்</span><span class="sub" lang="en">Map</span></h2>{/if}
		<p class="count">{countLine}</p>
		<div class="grid" class:seven={where === 'sheet'}>
			{#each psalms as p (p.n)}
				{@const t = themeOf.get(p.theme)!}
				{@const ok = isEmpty(sel) || matches(p)}
				<button type="button" class="cell" class:on={p.n === open} class:dim={!ok} aria-pressed={p.n === open} title="{ta ? 'சங்கீதம்' : 'Psalm'} {p.n} · {ta ? t.ta : t.en}" style="--tc: {t.color}" onclick={() => pick(p.n)}>{p.n}</button>
			{/each}
		</div>
		{#if where !== 'sheet'}<p class="note">{ta ? 'சங்கீதங்கள் தங்கள் இடத்திலேயே இருக்கும்; பொருந்தாதவை மங்கும்.' : 'Psalms stay in their places; filters fade the ones that don’t match.'}</p>{/if}
	</section>
{/snippet}

<div class="page">
	<header class="intro">
		<div>
			<span class="kicker">{ta ? 'சங்கீதங்கள் · 150 பாடல்கள்' : 'Psalms · 150 songs'}</span>
			<h1 lang="ta">சங்கீதங்களைக் கருப்பொருள் வாரியாக ஆராயுங்கள்</h1>
			<p>Every psalm on one map, coloured by theme. Pick a number to read it with C. H. Spurgeon’s commentary from The Treasury of David, or sing it from the 1650 psalter.</p>
		</div>
		<form class="goto" onsubmit={go}>
			<label for="goto">{ta ? 'சங்கீதத்திற்குச் செல்' : 'Go to psalm'}</label>
			<div>
				<input id="goto" bind:value={goto} inputmode="numeric" pattern="[0-9]*" maxlength="3" placeholder="1–150" autocomplete="off" />
				<button type="submit">{ta ? 'திற' : 'Open'}</button>
			</div>
		</form>
	</header>

	<div class="layout">
		<nav class="side" aria-label={ta ? 'சங்கீத வரைபடம்' : 'Psalm map'}>
			{@render map('side')}
		</nav>
		<div bind:this={cardEl} class="card-anchor">
			{#key open}
				<PsalmCard {index} psalm={current} prev={steps.prev} next={steps.next} onpick={pick} {ta} />
			{/key}
		</div>
		<aside class="right" aria-label={ta ? 'சங்கீத வரைபடம்' : 'Psalm map'}>
			{@render grid('right')}
		</aside>
	</div>
</div>

<!-- Phones: the psalm first; this bar steps through the psalms and opens the map. -->
<nav class="dock" aria-label={ta ? 'சங்கீதங்கள்' : 'Psalms'}>
	<button type="button" class="dock-step" aria-label="{ta ? 'சங்கீதம்' : 'Psalm'} {steps.prev}" onclick={() => pick(steps.prev)}>
		<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>{steps.prev}
	</button>
	<button type="button" class="dock-map" onclick={() => { menu = null; sheet?.showModal(); }}>
		<span class="swatch" aria-hidden="true">
			{#each psalms.slice(0, 10) as p (p.n)}<i style="--tc: {themeOf.get(p.theme)!.color}"></i>{/each}
		</span>
		<span class="label">
			<span lang={ta ? 'ta' : 'en'}>{ta ? '150 சங்கீதங்கள்' : 'All 150 psalms'}</span>
			<span class="sub">{ta ? 'வரைபடம் · வடிகட்டு' : 'Map and filters'}</span>
		</span>
		{#if count(sel)}<span class="badge">{count(sel)}</span>{/if}
	</button>
	<button type="button" class="dock-step" aria-label="{ta ? 'சங்கீதம்' : 'Psalm'} {steps.next}" onclick={() => pick(steps.next)}>
		{steps.next}<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
	</button>
</nav>

<dialog bind:this={sheet} class="sheet" aria-label={ta ? '150 சங்கீதங்கள்' : 'All 150 psalms'} onclick={(e) => { if (e.target === sheet) sheet?.close(); }}>
	<div class="sheet-head">
		<h2><span lang={ta ? 'ta' : 'en'}>{ta ? '150 சங்கீதங்கள்' : 'All 150 psalms'}</span></h2>
		<button type="button" class="x" aria-label={ta ? 'மூடு' : 'Close'} onclick={() => sheet?.close()}>
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
		</button>
	</div>
	<div class="sheet-body">
		{@render map('sheet')}
	</div>
	<div class="sheet-foot"><button type="button" class="primary" onclick={() => sheet?.close()}>{showLabel}</button></div>
</dialog>

<style>
	.page { max-width: 92rem; margin: 0 auto; display: flex; flex-direction: column; gap: 1.75rem; }
	.intro { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 1rem 2rem; padding: 0.5rem 0 1.5rem; border-bottom: var(--bw) solid var(--line); }
	.intro > div { max-width: 48rem; }
	.kicker { display: block; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.4rem; }
	h1 { font-family: var(--tamil); font-size: 2.1rem; font-weight: 600; margin: 0 0 0.4rem; letter-spacing: -0.01em; line-height: 1.2; text-wrap: balance; }
	.intro p { color: var(--ink-2); max-width: 44rem; margin: 0; font-size: 1.02rem; line-height: 1.6; }
	.goto { display: flex; flex-direction: column; gap: 0.35rem; }
	.goto label { font-size: 0.82rem; font-weight: 600; color: var(--ink-2); }
	.goto div { display: flex; gap: 0.5rem; }
	.goto input { width: 7.5rem; height: 44px; box-sizing: border-box; padding: 0 0.85rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: var(--surface); color: var(--ink); font: inherit; font-size: 1rem; font-variant-numeric: tabular-nums; }
	.goto input:focus { border-color: var(--accent); outline: none; }
	.goto button { height: 44px; padding: 0 1rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: var(--surface); color: var(--ink); font: inherit; font-weight: 600; cursor: pointer; }
	.goto button:hover { border-color: var(--accent); }

	/* The map beside the reading pane. */
	.layout { display: grid; grid-template-columns: minmax(20rem, 30rem) minmax(0, 1fr); gap: 2.5rem; align-items: start; }
	.side { position: sticky; top: calc(var(--header-h) + 1rem); max-height: calc(100vh - var(--header-h) - 2rem); overflow: auto; display: flex; flex-direction: column; gap: 1.4rem; padding: 0 0.25rem 1rem 0; }
	.block { display: flex; flex-direction: column; gap: 0.6rem; min-width: 0; }
	.card-anchor { min-width: 0; scroll-margin-top: calc(var(--header-h) + 1rem); }

	.h-row { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem 1rem; }
	h2 { margin: 0; font-size: 1.1rem; font-weight: 600; color: var(--amber); display: flex; gap: 0.55rem; align-items: baseline; }
	h2 [lang='ta'] { font-family: var(--tamil); }
	h2 .sub { font-size: 0.88rem; font-weight: 500; color: var(--muted); }
	.clear { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; font-size: 0.9rem; cursor: pointer; padding: 0.4rem 0; text-decoration: underline; text-underline-offset: 3px; }

	/* Theme colours from the design; lifted towards white on dark grounds. */
	.theme, .cell, .dock i { --tcx: var(--tc); }
	@media (prefers-color-scheme: dark) { :global(:root:not([data-theme='light'])) :is(.theme, .cell, .dock i) { --tcx: color-mix(in oklab, var(--tc) 70%, white); } }
	:global(:root[data-theme='dark']) :is(.theme, .cell, .dock i) { --tcx: color-mix(in oklab, var(--tc) 70%, white); }

	.themes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.4rem; }
	.theme { display: flex; align-items: center; gap: 0.65rem; min-height: 52px; padding: 0.35rem 0.75rem; border: var(--bw) solid var(--line); border-radius: 11px; background: var(--surface); color: var(--ink); cursor: pointer; text-align: left; font: inherit; transition: opacity 0.15s; }
	.theme i { flex: none; width: 12px; height: 12px; border-radius: 999px; background: var(--tcx); }
	.theme .names { display: flex; flex-direction: column; min-width: 0; line-height: 1.25; }
	.theme .a { font-weight: 600; font-size: 0.95rem; }
	.theme .b { font-size: 0.74rem; color: var(--muted); }
	.theme [lang='ta'] { font-family: var(--tamil); }
	.theme .n { margin-left: auto; font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
	.theme:hover { border-color: var(--accent); }
	.theme.on { border-color: var(--tcx); background: color-mix(in srgb, var(--tcx) 16%, var(--surface)); }
	.theme.dim { opacity: 0.6; }

	.menus { display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.menu { position: relative; display: inline-flex; align-items: center; gap: 0.45rem; min-height: 44px; padding: 0 0.8rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: var(--surface); color: var(--ink); font: inherit; cursor: pointer; }
	.menu .a { font-weight: 600; font-size: 0.95rem; }
	.menu .b { font-size: 0.78rem; color: var(--muted); }
	.menu [lang='ta'] { font-family: var(--tamil); }
	.menu svg { transition: transform 0.15s; }
	.menu[aria-expanded='true'] svg { transform: rotate(180deg); }
	.menu:hover, .menu[aria-expanded='true'] { border-color: var(--accent); }
	.menu.set { background: var(--accent-soft); }
	.badge { min-width: 20px; height: 20px; padding: 0 5px; box-sizing: border-box; border-radius: 999px; background: var(--accent); color: var(--on-accent); font-size: 0.72rem; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; font-variant-numeric: tabular-nums; }
	.panel { display: flex; flex-wrap: wrap; gap: 0.4rem; padding: 0.75rem; border: var(--bw) solid var(--line); border-radius: 12px; background: var(--surface-2); }
	.chip { display: inline-flex; flex-direction: column; align-items: flex-start; min-height: 44px; padding: 0.4rem 0.8rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: var(--surface); color: var(--ink); cursor: pointer; text-align: left; line-height: 1.3; font: inherit; }
	.chip:hover { border-color: var(--accent); }
	.chip .a { font-weight: 600; font-size: 0.92rem; }
	.chip .b { font-size: 0.72rem; color: var(--muted); }
	.chip [lang='ta'] { font-family: var(--tamil); }
	.chip.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.chip.on .b { color: var(--on-accent); opacity: 0.8; }

	.count { margin: 0; font-size: 0.86rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
	.grid { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 4px; }
	.grid.seven { grid-template-columns: repeat(7, minmax(0, 1fr)); }
	.cell { aspect-ratio: 1; min-height: 40px; padding: 0; border: 0; border-bottom: 3px solid var(--tcx); border-radius: 7px; background: color-mix(in srgb, var(--tcx) 14%, var(--surface)); color: var(--ink); font: inherit; font-weight: 600; font-size: 0.9rem; font-variant-numeric: tabular-nums; cursor: pointer; transition: opacity 0.2s; }
	.cell:hover { outline: 2px solid var(--accent); outline-offset: 1px; }
	.cell.dim { opacity: 0.2; }
	.cell.dim:hover { opacity: 0.6; }
	.cell.on { opacity: 1; background: var(--tcx); color: var(--bg); box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--tcx); }
	.note { margin: 0; font-size: 0.8rem; color: var(--muted); }

	.dock { display: none; }
	.sheet { width: 100%; max-width: 40rem; max-height: 88vh; margin: auto auto 0; padding: 0; border: 0; border-radius: 20px 20px 0 0; background: var(--surface-2); color: var(--ink); display: none; flex-direction: column; }
	.sheet[open] { display: flex; }
	.sheet::backdrop { background: var(--scrim); }
	.sheet-head { display: flex; align-items: center; gap: 1rem; padding: 0.9rem 0.75rem 0.5rem 1rem; }
	.sheet-head h2 { flex: 1; color: var(--ink); font-size: 1.2rem; }
	.sheet-head h2 [lang='ta'] { font-family: var(--tamil); }
	.x { width: 44px; height: 44px; border: 0; border-radius: 999px; background: var(--surface); color: var(--ink-2); display: flex; align-items: center; justify-content: center; cursor: pointer; }
	.sheet-body { overflow: auto; padding: 0.25rem 1rem 1rem; display: flex; flex-direction: column; gap: 1.1rem; }
	/* In the sheet the themes are one row that scrolls sideways, leaving room for the map. */
	.sheet-body .themes { display: flex; overflow-x: auto; margin: 0 -1rem; padding: 0 1rem 0.2rem; scrollbar-width: none; }
	.sheet-body .theme { flex: none; min-height: 44px; border-radius: 999px; padding: 0 0.9rem; }
	.sheet-body .theme .b { display: none; }
	.sheet-body .cell { min-height: 44px; }
	.sheet-body .cell.on { box-shadow: 0 0 0 2px var(--surface-2), 0 0 0 4px var(--tcx); }
	.sheet-foot { padding: 10px 16px calc(16px + env(safe-area-inset-bottom)); border-top: var(--bw) solid var(--line); }
	.primary { width: 100%; min-height: 50px; border: 0; border-radius: 12px; background: var(--accent); color: var(--on-accent); font: inherit; font-weight: 700; font-size: 1rem; cursor: pointer; font-variant-numeric: tabular-nums; }

	.right { display: none; }
	/* The heading and intro on one line where they fit. */
	@media (min-width: 80rem) {
		.intro > div { max-width: none; }
		h1 { white-space: nowrap; }
	}
	@media (min-width: 90rem) {
		.intro p { white-space: nowrap; max-width: none; font-size: 0.96rem; }
	}
	/* Large screens: filters, the psalm, and the map in a column of its own on the right. */
	@media (min-width: 100rem) {
		.page { max-width: 120rem; }
		.layout { grid-template-columns: minmax(16rem, 19rem) minmax(0, 1fr) minmax(24rem, 29rem); gap: 2.25rem; }
		.side .in-side { display: none; }
		.side .themes { grid-template-columns: minmax(0, 1fr); }
		.right { position: sticky; top: calc(var(--header-h) + 1rem); max-height: calc(100vh - var(--header-h) - 2rem); overflow: auto; display: flex; flex-direction: column; padding: 0 0.25rem 1rem 0; }
	}
	@media (max-width: 64rem) {
		.layout { grid-template-columns: minmax(18rem, 24rem) minmax(0, 1fr); gap: 1.75rem; }
	}
	/* Phones: the psalm first, the map in a sheet from the bar at the foot. */
	@media (max-width: 52rem) {
		.page { gap: 1rem; }
		/* Room under the footer for the bar. */
		:global(body:has(nav.dock)) { padding-bottom: 5rem; }
		.intro { padding-bottom: 1rem; }
		.intro p, .goto { display: none; }
		h1 { font-size: 1.5rem; margin: 0; }
		.layout { grid-template-columns: minmax(0, 1fr); }
		.side { display: none; }
		.dock { position: fixed; z-index: 20; left: 0; right: 0; bottom: 0; display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 0.75rem calc(0.75rem + env(safe-area-inset-bottom)); background: var(--surface-2); border-top: var(--bw) solid var(--line); }
		.dock-step { flex: none; display: inline-flex; align-items: center; justify-content: center; gap: 2px; width: 56px; height: 52px; border: var(--bw) solid var(--line-2); border-radius: 12px; background: none; color: var(--ink-2); font: inherit; font-weight: 600; font-variant-numeric: tabular-nums; cursor: pointer; }
		.dock-map { position: relative; flex: 1; min-width: 0; display: flex; align-items: center; gap: 0.7rem; height: 52px; padding: 0 0.9rem; border: var(--bw) solid var(--line-2); border-radius: 12px; background: var(--surface); color: var(--ink); font: inherit; cursor: pointer; text-align: left; }
		.swatch { flex: none; display: grid; grid-template-columns: repeat(5, 6px); gap: 2px; }
		.swatch i { height: 6px; border-radius: 1px; background: var(--tcx); }
		.label { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; }
		.label > span:first-child { font-weight: 600; font-size: 0.95rem; }
		.label [lang='ta'] { font-family: var(--tamil); }
		.label > span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
		.label .sub { font-size: 0.76rem; color: var(--muted); }
		.dock-map .badge { position: absolute; top: -6px; right: -6px; }
	}
	@media (prefers-reduced-motion: reduce) { .cell, .theme, .menu svg { transition: none; } }
</style>

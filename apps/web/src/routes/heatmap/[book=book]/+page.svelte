<script lang="ts">
	// Per-book heatmap: one cell per verse, grouped by chapter (R-2.2).
	import { onMount } from 'svelte';
	import { chapterUrl } from '$lib/content/manifest';
	import { bookHeat, bucket, type BookHeat } from '$lib/content/heat';
	import { loadChapter } from '$lib/content/load';
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const name = $derived(ta ? data.book.name_ta : data.book.name_en);
	const version = $derived(settings.value.version);
	let heat = $state<BookHeat | null>(null);
	let verseCounts = $state<Record<number, number>>({});
	onMount(async () => {
		heat = await bookHeat(fetch, data.book.slug);
		// Verse counts per chapter come from the chapter JSON (last verse number).
		const counts: Record<number, number> = {};
		await Promise.all(
			Array.from({ length: data.book.chapters }, (_, i) => i + 1).map(async (c) => {
				try {
					const ch = await loadChapter(fetch, version.toUpperCase(), data.book.code, c);
					let max = 0;
					for (const b of ch.blocks) if (b.type === 'para') for (const s of b.segments) { const n = Number(s.id?.split('.')[2]); if (n > max) max = n; }
					counts[c] = max;
				} catch { counts[c] = 0; }
			})
		);
		verseCounts = counts;
	});
	const values = $derived(heat ? Object.values(heat).flatMap((c) => Object.values(c)) : []);
</script>

<svelte:head>
	<title>{name} · {ta ? 'வெப்ப வரைபடம்' : 'Heatmap'} · Tamil Scripture</title>
	<meta name="description" content="Verses in {data.book.name_en} that readers highlight most." />
</svelte:head>

<nav class="crumbs" aria-label="Breadcrumb"><a href="/heatmap">{ta ? 'வெப்ப வரைபடம்' : 'Heatmap'}</a> <span aria-hidden="true">›</span> <span aria-current="page" lang={ta ? 'ta' : 'en'}>{name}</span></nav>
<h1 lang={ta ? 'ta' : 'en'}>{name}</h1>
<p class="lede">{ta ? 'ஒவ்வொரு கட்டமும் ஒரு வசனம். தொட்டால் அந்த வசனம் திறக்கும்.' : 'Each cell is a verse. Tap a cell to open it.'}</p>

{#if !heat || !Object.keys(verseCounts).length}
	<p class="muted">…</p>
{:else}
	{#each Array.from({ length: data.book.chapters }, (_, i) => i + 1) as c (c)}
		<div class="chapter">
			<a class="ch" href={chapterUrl(version, data.book, c)}>{c}</a>
			<div class="cells">
				{#each Array.from({ length: verseCounts[c] ?? 0 }, (_, i) => i + 1) as v (v)}
					{@const n = heat?.[String(c)]?.[String(v)] ?? 0}
					<a class="cell b{bucket(n, values)}" href={chapterUrl(version, data.book, c, String(v))} title="{data.book.name_en} {c}:{v}{n ? ` · ${n}` : ''}" aria-label="{data.book.name_en} {c}:{v}"></a>
				{/each}
			</div>
		</div>
	{/each}
	{#if !values.length}<p class="muted">{ta ? 'இந்தப் புத்தகத்தில் இன்னும் போதுமான அடிக்கோடுகள் இல்லை.' : 'Not enough highlights in this book yet.'}</p>{/if}
{/if}

<style>
	.crumbs { font-size: 0.9rem; color: var(--muted); margin-bottom: 0.6rem; display: flex; gap: 0.5rem; }
	.crumbs a { color: inherit; }
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0 0 0.3rem; }
	.lede { color: var(--muted); font-family: var(--tamil); }
	.chapter { display: grid; grid-template-columns: 2.5rem 1fr; gap: 0.5rem; align-items: start; padding: 0.25rem 0; }
	.ch { font-variant-numeric: tabular-nums; text-decoration: none; color: var(--muted); font-size: 0.85rem; padding-top: 1px; }
	.cells { display: flex; flex-wrap: wrap; gap: 2px; }
	.cell { display: block; width: 12px; height: 12px; border-radius: 2px; background: var(--surface-2); }
	.b1 { background: rgba(var(--heat-rgb), 0.2); } .b2 { background: rgba(var(--heat-rgb), 0.4); } .b3 { background: rgba(var(--heat-rgb), 0.65); } .b4 { background: var(--accent); }
	.muted { color: var(--muted); }
</style>

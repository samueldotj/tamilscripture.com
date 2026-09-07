<script lang="ts">
	import { onMount } from 'svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { allHighlights, COLORS, type Highlight, type HighlightColor } from '$lib/personal/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let items = $state<Highlight[]>([]);
	let color = $state<HighlightColor | ''>('');
	let loading = $state(true);
	onMount(async () => { try { items = await allHighlights(); } finally { loading = false; } });

	const filtered = $derived(color ? items.filter((h) => h.color === color) : items);
	const byBook = $derived.by(() => {
		const m = new Map<string, Highlight[]>();
		for (const h of filtered) { if (!m.has(h.book)) m.set(h.book, []); m.get(h.book)!.push(h); }
		return [...m.entries()].sort((a, b) => findBook(a[0])!.order - findBook(b[0])!.order);
	});
	function label(h: Highlight) {
		const b = findBook(h.book)!;
		return `${ta ? b.name_ta : b.name_en} ${h.chapter}:${h.verse_start}${h.verse_end !== h.verse_start ? `-${h.verse_end}` : ''}`;
	}
	function href(h: Highlight) {
		return chapterUrl(settings.value.version, findBook(h.book)!, h.chapter, h.verse_end !== h.verse_start ? `${h.verse_start}-${h.verse_end}` : `${h.verse_start}`);
	}
</script>

<svelte:head><title>{ta ? 'அடிக்கோடுகள்' : 'Highlights'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1>{ta ? 'அடிக்கோடுகள்' : 'Highlights'} <span class="n">{items.length}</span></h1>
	<div class="filter" role="radiogroup" aria-label={ta ? 'நிறம்' : 'Colour'}>
		<button type="button" role="radio" aria-checked={color === ''} class:on={color === ''} onclick={() => (color = '')}>{ta ? 'எல்லாம்' : 'All'}</button>
		{#each COLORS as c (c)}
			<button type="button" role="radio" aria-checked={color === c} class="swatch {c}" class:on={color === c} aria-label={c} onclick={() => (color = c)}></button>
		{/each}
	</div>
</div>

{#if loading}
	<p class="muted">…</p>
{:else if !filtered.length}
	<p class="muted">{ta ? 'அடிக்கோடுகள் இல்லை. வசன எண்ணைத் தொட்டு ஒரு நிறத்தைத் தேர்வு செய்யுங்கள்.' : 'No highlights yet. Tap a verse number and pick a colour.'}</p>
{:else}
	{#each byBook as [code, hs] (code)}
		<section>
			<h2 lang={ta ? 'ta' : 'en'}>{ta ? findBook(code)!.name_ta : findBook(code)!.name_en}</h2>
			<ul>
				{#each hs as h (h.id)}
					<li><span class="dot {h.color}"></span><a href={href(h)} lang={ta ? 'ta' : 'en'}>{label(h)}</a></li>
				{/each}
			</ul>
		</section>
	{/each}
{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0; }
	h1 .n { color: var(--muted); font-size: 1rem; font-weight: 400; }
	.filter { display: flex; gap: 0.4rem; align-items: center; }
	.filter button { border: 1px solid var(--line); background: var(--surface); color: inherit; border-radius: 999px; padding: 0.35rem 0.8rem; min-height: 36px; cursor: pointer; font-family: var(--tamil); }
	.filter button.on { border-color: var(--ink); }
	.swatch { width: 30px; height: 30px; min-height: 30px; padding: 0; border-radius: 50%; }
	.swatch.yellow, .dot.yellow { background: var(--hl-yellow); } .swatch.green, .dot.green { background: var(--hl-green); } .swatch.blue, .dot.blue { background: var(--hl-blue); } .swatch.pink, .dot.pink { background: var(--hl-pink); }
	h2 { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 1.2rem 0 0.4rem; font-family: var(--tamil); }
	ul { list-style: none; padding: 0; margin: 0; }
	li { display: flex; gap: 0.6rem; align-items: center; padding: 0.4rem 0; border-top: 1px solid var(--line); }
	.dot { width: 12px; height: 12px; border-radius: 50%; flex: none; }
	li a { font-family: var(--tamil); text-decoration: none; font-weight: 600; }
	.muted { color: var(--muted); }
</style>

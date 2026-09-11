<script lang="ts">
	// Whole-Bible heatmap: one cell per chapter (R-2.2).
	import { onMount } from 'svelte';
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import { allHeat, bucket, type AllHeat } from '$lib/content/heat';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let heat = $state<AllHeat | null>(null);
	onMount(async () => { heat = await allHeat(fetch); });
	const values = $derived(heat ? Object.values(heat).flatMap((c) => Object.values(c)) : []);
	const version = $derived(settings.value.version);
</script>

<svelte:head>
	<title>{ta ? 'வெப்ப வரைபடம்' : 'Heatmap'} · Tamil Scripture</title>
	<meta name="description" content="Which chapters of the Bible readers highlight most, across the whole community." />
</svelte:head>

<h1>{ta ? 'சமூக அடிக்கோட்டு வெப்ப வரைபடம்' : 'Community highlight heatmap'}</h1>
<p class="lede">{ta ? 'ஒவ்வொரு கட்டமும் ஒரு அதிகாரம். நிறம் அதிகமானால், அதிக வாசகர்கள் அதில் வசனங்களை அடிக்கோடிட்டுள்ளனர். எண்ணிக்கைகள் அநாமதேயம்; மூன்றுக்குக் குறைவான வாசகர்கள் இருந்தால் காட்டப்படாது. ஒவ்வொரு மணி நேரமும் புதுப்பிக்கப்படுகிறது.' : 'Each cell is a chapter. Darker means more readers have highlighted verses in it. Counts are anonymous, hidden below three readers, and refreshed hourly.'}</p>

{#if !heat}
	<p class="muted">…</p>
{:else if !values.length}
	<p class="muted">{ta ? 'இன்னும் போதுமான அடிக்கோடுகள் இல்லை.' : 'Not enough highlights yet.'}</p>
{:else}
	{#each ['OT', 'NT'] as t (t)}
		<h2>{t === 'OT' ? (ta ? 'பழைய ஏற்பாடு' : 'Old Testament') : (ta ? 'புதிய ஏற்பாடு' : 'New Testament')}</h2>
		<div class="books">
			{#each manifest.books.filter((b) => b.testament === t) as b (b.code)}
				<div class="book">
					<a class="name" href="/heatmap/{b.slug}" lang={ta ? 'ta' : 'en'}>{ta ? b.name_ta : b.name_en}</a>
					<div class="cells" style="grid-template-columns: repeat({Math.min(b.chapters, 25)}, 1fr)">
						{#each Array.from({ length: b.chapters }, (_, i) => i + 1) as c (c)}
							{@const n = heat?.[b.code]?.[c] ?? 0}
							<a class="cell b{bucket(n, values)}" href={chapterUrl(version, b, c)} title="{b.name_en} {c}{n ? ` · ${n}` : ''}" aria-label="{b.name_en} {c}"></a>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{/each}
	<p class="legend"><span class="cell b0"></span> 0 <span class="cell b1"></span> <span class="cell b2"></span> <span class="cell b3"></span> <span class="cell b4"></span> {ta ? 'அதிகம்' : 'most'}</p>
{/if}

<style>
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0 0 0.5rem; }
	.lede { color: var(--muted); max-width: 44rem; font-family: var(--tamil); }
	h2 { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 1.5rem 0 0.6rem; }
	.books { display: grid; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); gap: 0.6rem 1.2rem; }
	.book { display: grid; grid-template-columns: 7rem 1fr; gap: 0.5rem; align-items: center; }
	.name { font-size: 0.85rem; text-decoration: none; color: inherit; font-family: var(--tamil); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.cells { display: grid; gap: 2px; }
	.cell { display: block; aspect-ratio: 1; border-radius: 2px; background: var(--surface-2); min-width: 6px; }
	.b1 { background: rgba(var(--heat-rgb), 0.2); } .b2 { background: rgba(var(--heat-rgb), 0.4); } .b3 { background: rgba(var(--heat-rgb), 0.65); } .b4 { background: var(--accent); }
	.legend { display: flex; gap: 0.35rem; align-items: center; font-size: 0.8rem; color: var(--muted); margin-top: 1.5rem; }
	.legend .cell { width: 14px; }
	.muted { color: var(--muted); }
</style>

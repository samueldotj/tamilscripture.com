<script lang="ts">
	// Atlas sample: Abraham's journeys on the journey map, and a few other journeys.
	import { loadJourneys, loadMapSvg } from '$lib/entities/load';
	import type { Journey } from '$lib/entities/types';
	import Card from './Card.svelte';

	let { lang }: { lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');
	const SHOWN = ['abraham', 'exodus', 'ruth', 'paul-1'];

	let svg = $state<string | null>(null);
	let journeys = $state<Journey[]>([]);
	function load() {
		loadMapSvg(fetch, 'journey/abraham').then((s) => (svg = s)).catch(() => {});
		loadJourneys(fetch)
			.then((all) => (journeys = SHOWN.flatMap((id) => all.filter((j) => j.id === id))))
			.catch(() => {});
	}
</script>

<Card ta="வேதாகம வரைபடம்" en="Atlas" tag={ta ? 'ஆபிரகாமின் பயணங்கள்' : "Abraham's journeys"} href="/atlas" cta={ta ? 'வரைபடத்தைத் திற' : 'Open the atlas'} {lang} onvisible={load}>
	<a class="map-link" href="/atlas/abraham" aria-label={ta ? 'ஆபிரகாமின் பயணங்கள்' : "Abraham's journeys"}>
		{#if svg}{@html svg}{:else}<div class="map-ph" aria-hidden="true"></div>{/if}
	</a>
	{#if journeys.length}
		<ul class="chips">
			{#each journeys as j (j.id)}
				<li><a class="chip" class:on={j.id === 'abraham'} href="/atlas/{j.id}" {lang}>{ta ? j.name_ta : j.name_en}</a></li>
			{/each}
		</ul>
	{/if}
</Card>

<style>
	.map-link { display: block; }
	.map-link :global(svg) { display: block; width: 100%; height: auto; }
	.map-ph { aspect-ratio: 800 / 520; border-radius: var(--r-l); border: var(--bw) solid var(--line); background: var(--map-water); }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.chip { display: inline-flex; align-items: center; min-height: 40px; padding: 0 0.9rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font-size: 0.9rem; text-decoration: none; }
	.chip[lang='ta'] { font-family: var(--tamil); }
	.chip:hover, .chip.on { border-color: var(--accent); }
	.chip.on { background: var(--accent-soft); }
</style>

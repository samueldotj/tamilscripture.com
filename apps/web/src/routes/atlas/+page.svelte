<script lang="ts">
	import { journeyStyle } from '$lib/entities/journeys';
	import { placeName } from '$lib/entities/load';
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const lang = $derived(settings.value.uiLang);
	function period(id: string) {
		const g = data.glossary?.periods[id];
		return g ? (ta ? g.ta : g.en) : id;
	}
</script>

<svelte:head>
	<title>{ta ? 'வேதாகம வரைபடம்' : 'Bible atlas'} · Tamil Scripture</title>
	<meta name="description" content="Biblical places on outline maps: the Exodus, the ministry of Jesus and Paul's journeys, with every place linked to the verses that name it." />
	<link rel="canonical" href="https://www.tamilscripture.com/atlas" />
</svelte:head>

<section class="hero">
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'வேதாகம வரைபடம்' : 'Bible atlas'}</h1>
	<p class="lede" lang={ta ? 'ta' : 'en'}>{ta ? `${data.count.toLocaleString('ta-IN')} வேதாகம இடங்கள், ஒவ்வொன்றும் அதைக் குறிப்பிடும் வசனங்களுடன். பயணங்களைப் பின்தொடரலாம், அல்லது முழு வரைபடத்தை ஆராயலாம்.` : `${data.count.toLocaleString()} biblical places, each linked to the verses that name it. Follow a journey, or explore the whole map.`}</p>
	<a class="chip primary" href="/atlas/explore">
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/></svg>
		<span lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடத்தை ஆராய்' : 'Explore the map'}</span>
	</a>
</section>

<section>
	<h2 class="kicker"><span lang="ta">பயணங்கள்</span> · Journeys</h2>
	<ul class="journeys">
		{#each data.journeys as j, i (j.id)}
			<li>
				<a class="card journey" href="/atlas/{j.id}" style="--j: {journeyStyle(i).color}">
					<span class="period" lang={ta ? 'ta' : 'en'}>{period(j.period)}</span>
					<span class="name" lang={ta ? 'ta' : 'en'}>{ta ? j.name_ta : j.name_en}</span>
					<span class="meta" lang={ta ? 'ta' : 'en'}>{j.stops.length} {ta ? 'இடங்கள்' : 'stops'}</span>
				</a>
			</li>
		{/each}
	</ul>
</section>

{#if data.top.length}
	<section>
		<h2 class="kicker"><span lang="ta">அதிகம் குறிப்பிடப்படும் இடங்கள்</span> · Most-mentioned places</h2>
		<ul class="chips">
			{#each data.top as p (p.id)}
				<li><a class="chip round" href="/place/{p.id}" lang={ta && p.name_ta ? 'ta' : 'en'}>{placeName(p, lang)} <span class="n">{p.mentions}</span></a></li>
			{/each}
		</ul>
	</section>
{/if}

<p class="credit">OpenBible.info Bible Geocoding, CC BY 4.0 · Natural Earth · Routes: UBS Project MARBLE (Leen Ritmeyer), © United Bible Societies 2023, CC BY-SA 4.0</p>

<style>
	.hero { margin: 0.5rem 0 2rem; display: grid; gap: 0.6rem; justify-items: start; }
	h1 { font-size: 2.2rem; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.lede { color: var(--ink-2); max-width: 40rem; margin: 0 0 0.4rem; font-size: 1.02rem; line-height: 1.65; }
	.lede[lang='ta'] { font-family: var(--tamil); }
	.hero .chip { min-height: 48px; border-radius: var(--r-l); padding: 0 1.2rem; font-size: 1rem; }
	section { margin-bottom: 2rem; }
	h2.kicker { margin: 0 0 0.8rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.journeys { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: 0.75rem; }
	/* The stripe is the journey's colour on the explore map. */
	.journey { display: grid; gap: 0.25rem; padding: 1rem 1.1rem 1rem 1.4rem; text-decoration: none; color: inherit; position: relative; overflow: hidden; }
	.journey::before { content: ''; position: absolute; inset: 0 auto 0 0; width: 5px; background: var(--j); }
	.journey:hover { border-color: var(--accent); }
	.period { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--amber); }
	.period[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.03em; }
	.name { font-size: 1.1rem; font-weight: 600; line-height: 1.35; }
	.name[lang='ta'] { font-family: var(--tamil); }
	.meta { font-size: 0.8rem; color: var(--muted); }
	.meta[lang='ta'] { font-family: var(--tamil); }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.45rem; }
	.chips .chip { font-weight: 500; min-height: 38px; }
	.chips .chip[lang='ta'] { font-family: var(--tamil); }
	.chips .n { font-size: 0.72rem; color: var(--muted); }
	.credit { font-size: 0.75rem; color: var(--muted); }
</style>

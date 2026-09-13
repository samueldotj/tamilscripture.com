<script lang="ts">
	import { settings } from '$lib/settings/store.svelte';
	import { SOURCES, SOURCE_ORDER, sourceOf } from '$lib/entities/sources';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	let picked = $state<string | null>(null);
	const letter = $derived(picked ?? data.letter);
	let pickedSource = $state<string | null>(null);
	const source = $derived(pickedSource ?? data.source);
	let q = $state('');
	const pool = $derived(source === 'all' ? data.articles : data.articles.filter((a) => a.source === source));
	const shown = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		if (needle) return pool.filter((a) => a.title.toLowerCase().includes(needle)).slice(0, 200);
		return pool.filter((a) => (a.title[0]?.toUpperCase() ?? '#') === letter);
	});
	const total = $derived(data.articles.length.toLocaleString('en-IN'));
	const description = $derived(
		ta
			? `வேதாகம அகராதி: Aquifer, ஈஸ்டன், ஸ்மித் அகராதிகளின் ${total} கட்டுரைகள், இடங்கள் மற்றும் நபர்களுடன் இணைக்கப்பட்டவை. தமிழ் வடிவங்கள் சமூக மதிப்பாய்வில்.`
			: `Bible dictionary: ${total} articles from the Aquifer Open Bible Dictionary, Easton’s and Smith’s, linked to places and people. Tamil versions under community review.`
	);
	function setSource(s: string) {
		pickedSource = s;
		const u = new URL(location.href);
		if (s === 'all') u.searchParams.delete('s'); else u.searchParams.set('s', s);
		history.replaceState(null, '', u);
	}
</script>

<svelte:head>
	<title>{ta ? 'வேதாகம அகராதி' : 'Bible Dictionary'} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href="https://www.tamilscripture.com/dictionary" />
</svelte:head>

<article class="dict">
	<header class="head">
		<div class="kicker"><span lang="ta">அகராதி</span> · Dictionary</div>
		<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'வேதாகம அகராதி' : 'Bible Dictionary'}</h1>
		<p class="lede" lang={ta ? 'ta' : 'en'}>
			{#if ta}
				மூன்று அகராதிகளின் <span class="n">{total}</span> கட்டுரைகள். ஆங்கில மூலம்; தமிழ் வடிவங்கள் வரைவாக வந்து சமூக மதிப்பாய்வுக்குப் பின் வெளியிடப்படும். <span class="badge" lang="en">EN</span>
			{:else}
				<span class="n">{total}</span> articles from three dictionaries. English source text; Tamil versions arrive as drafts and are published after community review. <span class="badge">EN</span>
			{/if}
		</p>
		<div class="sources" role="group" aria-label={ta ? 'அகராதி' : 'Dictionary'}>
			<button type="button" class:on={source === 'all'} onclick={() => setSource('all')} lang={ta ? 'ta' : 'en'}>{ta ? 'எல்லாம்' : 'All'}</button>
			{#each SOURCE_ORDER.filter((k) => data.counts[k]) as k (k)}
				<button type="button" class:on={source === k} onclick={() => setSource(k)} title={SOURCES[k].name}>{SOURCES[k].short} <span class="cnt">{data.counts[k].toLocaleString('en-IN')}</span></button>
			{/each}
		</div>
	</header>

	<div class="controls">
		<input class="field" type="search" bind:value={q} placeholder={ta ? 'தலைப்பில் தேடு' : 'Find a title'} aria-label={ta ? 'தலைப்பில் தேடு' : 'Find a title'} autocomplete="off" />
		<nav class="letters" aria-label={ta ? 'எழுத்து' : 'Letter'}>
			{#each data.letters as l (l)}
				<a href="/dictionary?l={l}" aria-current={l === letter && !q ? 'page' : undefined} onclick={(e) => { e.preventDefault(); q = ''; picked = l; history.replaceState(null, '', `/dictionary?l=${l}`); }}>{l}</a>
			{/each}
		</nav>
	</div>

	{#if shown.length === 0}
		<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'பொருந்தும் தலைப்புகள் இல்லை.' : 'No matching titles.'}</p>
	{:else}
		<ul class="list">
			{#each shown as a (a.id)}
				<li>
					<a href="/dictionary/{a.id}">{a.title}{#if source === 'all'} <span class="src">{sourceOf(a.source).short}</span>{/if}</a>
					{#if a.entities?.length}<span class="linked" title={a.entities.join(', ')} aria-label={ta ? 'இணைக்கப்பட்ட பெயர்' : 'linked name'}>⌁</span>{/if}
				</li>
			{/each}
		</ul>
	{/if}

	<div class="credits">
		{#each SOURCE_ORDER.filter((k) => data.counts[k]) as k (k)}
			<p class="source"><a href={SOURCES[k].url}>{SOURCES[k].name}</a> ({SOURCES[k].year}) · {SOURCES[k].attribution.split(' · ').slice(1).join(' · ') || (ta ? SOURCES[k].licence_ta : SOURCES[k].licence_en)}{#if SOURCES[k].sharealike} · <span lang={ta ? 'ta' : 'en'}>{ta ? 'இதன் தமிழ் வடிவங்களும் CC BY-SA 4.0' : 'Tamil versions of it are also CC BY-SA 4.0'}</span>{/if}</p>
		{/each}
	</div>
</article>

<style>
	.dict { max-width: 60rem; }
	.head { margin-bottom: 1.2rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	h1 { font-size: 2.2rem; font-weight: 600; margin: 0.3rem 0 0.5rem; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.lede { margin: 0; color: var(--ink-2); max-width: 42rem; line-height: 1.6; }
	.lede[lang='ta'] { font-family: var(--tamil); }
	.lede .n { font-weight: 600; }
	.badge { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; border: 1px solid var(--line-2); border-radius: 6px; padding: 0.05rem 0.4rem; color: var(--muted); vertical-align: middle; }
	.sources { display: inline-flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.9rem; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.sources button { border: 0; border-radius: 9px; padding: 0.4rem 0.8rem; background: transparent; color: var(--muted); font: inherit; font-size: 0.82rem; font-weight: 600; cursor: pointer; min-height: 36px; }
	.sources button[lang='ta'] { font-family: var(--tamil); }
	.sources button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.sources .cnt { font-weight: 400; margin-left: 0.2rem; }
	.list .src { font-size: 0.66rem; font-weight: 600; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.35rem; margin-left: 0.3rem; vertical-align: middle; }
	.credits { margin-top: 1.5rem; display: grid; gap: 0.3rem; }
	.controls { display: grid; gap: 0.8rem; margin: 1.2rem 0; }
	.field { font: inherit; padding: 0.6rem 0.9rem; border: 1px solid var(--line); border-radius: var(--r-s); background: var(--surface); color: inherit; max-width: 22rem; min-height: 44px; }
	.letters { display: flex; flex-wrap: wrap; gap: 0.25rem; }
	.letters a { min-width: 2.1rem; min-height: 2.1rem; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; text-decoration: none; font-weight: 600; color: var(--ink-2); border: 1px solid transparent; }
	.letters a:hover { border-color: var(--line); }
	.letters a[aria-current='page'] { background: var(--ink); color: var(--paper, var(--surface)); }
	.list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); gap: 0.15rem 1.5rem; }
	.list li { padding: 0.35rem 0; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; gap: 0.5rem; }
	.list a { text-decoration: none; font-weight: 500; }
	.list a:hover { color: var(--accent); }
	.linked { color: var(--accent); font-size: 0.8rem; }
	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.source { margin: 0; font-size: 0.78rem; color: var(--muted); }
	.source [lang='ta'] { font-family: var(--tamil); }
	.source a { color: inherit; }
</style>

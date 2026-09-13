<script lang="ts">
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	let picked = $state<string | null>(null);
	const letter = $derived(picked ?? data.letter);
	let q = $state('');
	const shown = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		if (needle) return data.articles.filter((a) => a.title.toLowerCase().includes(needle)).slice(0, 200);
		return data.articles.filter((a) => (a.title[0]?.toUpperCase() ?? '#') === letter);
	});
	const sources = $derived({ eastons: { name: 'Easton’s Bible Dictionary', year: '1897', licence: ta ? 'பொது உரிமை' : 'public domain' } });
	const description = $derived(
		ta
			? 'வேதாகம அகராதி: ஈஸ்டனின் 3,962 கட்டுரைகள், இடங்கள் மற்றும் நபர்களுடன் இணைக்கப்பட்டவை. தமிழ் வடிவங்கள் சமூக மதிப்பாய்வில்.'
			: 'Bible dictionary: 3,962 articles from Easton’s Bible Dictionary, linked to places and people. Tamil versions under community review.'
	);
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
				{sources.eastons.name} ({sources.eastons.year}, {sources.eastons.licence}) கட்டுரைகள் <span class="n">{data.articles.length.toLocaleString('en-IN')}</span>. ஆங்கில மூலம்; தமிழ் வடிவங்கள் வரைவாக வந்து சமூக மதிப்பாய்வுக்குப் பின் வெளியிடப்படும். <span class="badge" lang="en">EN</span>
			{:else}
				<span class="n">{data.articles.length.toLocaleString('en-IN')}</span> articles from {sources.eastons.name} ({sources.eastons.year}, {sources.eastons.licence}). English source text; Tamil versions arrive as drafts and are published after community review. <span class="badge">EN</span>
			{/if}
		</p>
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
					<a href="/dictionary/{a.id}">{a.title}</a>
					{#if a.entities?.length}<span class="linked" title={a.entities.join(', ')} aria-label={ta ? 'இணைக்கப்பட்ட பெயர்' : 'linked name'}>⌁</span>{/if}
				</li>
			{/each}
		</ul>
	{/if}

	<p class="source">Easton’s Bible Dictionary (1897), public domain · dataset by <a href="https://github.com/neuu-org/bible-dictionary-dataset">NEUU</a>, CC BY 4.0</p>
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
	.source { margin: 1.5rem 0 0; font-size: 0.78rem; color: var(--muted); }
	.source a { color: inherit; }
</style>

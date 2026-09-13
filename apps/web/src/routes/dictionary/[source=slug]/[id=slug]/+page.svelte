<script lang="ts">
	import { settings } from '$lib/settings/store.svelte';
	import { placeName } from '$lib/entities/load';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const a = $derived(data.article);
	const sourceName = $derived(a.source === 'eastons' ? 'Easton’s Bible Dictionary (1897)' : a.source);
	const hasTa = $derived(a.paragraphs.some((p) => p.ta));
	const description = $derived((a.paragraphs[0]?.ta ?? a.paragraphs[0]?.text ?? '').slice(0, 160));
</script>

<svelte:head>
	<title>{a.title} · {ta ? 'அகராதி' : 'Dictionary'} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com/dictionary/${a.id}`} />
	<meta property="og:title" content={a.title} />
	<meta property="og:description" content={description} />
</svelte:head>

<article class="art">
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a> <span aria-hidden="true">›</span>
		<a href="/dictionary?l={a.title[0]?.toUpperCase()}" lang={ta ? 'ta' : 'en'}>{ta ? 'அகராதி' : 'Dictionary'}</a> <span aria-hidden="true">›</span>
		<span aria-current="page">{a.title}</span>
	</nav>

	<header class="head">
		<div class="kicker">{sourceName} <span class="badge" title={hasTa ? (ta ? 'தமிழ் வரைவு உள்ளது' : 'Tamil draft available') : (ta ? 'ஆங்கிலம் மட்டும்' : 'English only')}>{hasTa ? 'TA' : 'EN'}</span></div>
		<h1>{a.title}</h1>
		{#if data.linked.length}
			<ul class="chips" aria-label={ta ? 'இணைக்கப்பட்ட பெயர்கள்' : 'Linked names'}>
				{#each data.linked as l (l.ref)}
					<li>
						<a class="chip round" href="/{l.ref}" lang={ta && l.name_ta ? 'ta' : 'en'}>
							<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								{#if l.kind === 'place'}<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>{:else}<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>{/if}
							</svg>
							{placeName(l, ta ? 'ta' : 'en')}
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</header>

	<div class="body">
		{#each a.paragraphs as p (p.id)}
			<div class="para" id={p.id.split('#')[1]}>
				{#if p.ta}
					<p lang="ta" class="ta">{p.ta}</p>
					<details class="src"><summary lang={ta ? 'ta' : 'en'}>{ta ? 'ஆங்கில மூலம்' : 'English source'}</summary><p lang="en">{p.text}</p></details>
					<span class="prov" lang={ta ? 'ta' : 'en'}>{ta ? 'AI வரைவு' : 'AI draft'}</span>
				{:else}
					<p lang="en">{p.text}</p>
				{/if}
			</div>
		{/each}
	</div>

	<footer class="foot">
		<p class="source">{a.attribution}</p>
		<p class="note" lang={ta ? 'ta' : 'en'}>{ta ? 'தமிழ் வடிவம் இன்னும் இல்லை. வரைவுகள் சமூக மதிப்பாய்வுக்குப் பின் இங்கே வெளியிடப்படும்.' : hasTa ? 'Tamil text is an unreviewed draft; corrections are published after community review.' : 'No Tamil version yet. Drafts are published here after community review.'}</p>
	</footer>
</article>

<style>
	.art { max-width: 46rem; }
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: var(--accent); font-weight: 600; text-decoration: none; }
	.crumbs [lang='ta'] { font-family: var(--tamil); }
	.head { margin-bottom: 1.4rem; }
	.badge { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; border: 1px solid var(--line-2); border-radius: 6px; padding: 0.05rem 0.4rem; color: var(--muted); margin-left: 0.5rem; vertical-align: middle; }
	h1 { font-size: 2.2rem; font-weight: 600; margin: 0.3rem 0 0.6rem; line-height: 1.2; letter-spacing: -0.01em; }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.chips .chip { min-height: 34px; font-weight: 500; font-size: 0.85rem; padding: 0.25rem 0.75rem; display: inline-flex; gap: 0.35rem; align-items: center; }
	.chips .chip[lang='ta'] { font-family: var(--tamil); }
	.body { display: grid; gap: 1.1rem; }
	.para { position: relative; }
	.para p { margin: 0; line-height: 1.75; font-size: 1.05rem; }
	.para p.ta { font-family: var(--tamil); font-size: 1.15rem; line-height: 1.9; }
	.src { margin-top: 0.4rem; font-size: 0.92rem; color: var(--ink-2); }
	.src summary { cursor: pointer; color: var(--muted); font-size: 0.8rem; }
	.src summary[lang='ta'] { font-family: var(--tamil); }
	.src p { margin-top: 0.3rem; font-size: 0.95rem; }
	.prov { display: inline-block; margin-top: 0.3rem; font-size: 0.7rem; color: var(--amber); border: 1px solid var(--amber); border-radius: 999px; padding: 0 0.45rem; }
	.prov[lang='ta'] { font-family: var(--tamil); }
	.foot { margin-top: 2rem; border-top: 1px solid var(--line); padding-top: 0.9rem; display: grid; gap: 0.4rem; }
	.source, .note { margin: 0; font-size: 0.78rem; color: var(--muted); }
	.note[lang='ta'] { font-family: var(--tamil); }
</style>

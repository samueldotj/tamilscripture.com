<script lang="ts">
	import RefText from '$lib/refs/RefText.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { placeName } from '$lib/entities/load';
	import SuggestControl from '$lib/community/SuggestControl.svelte';
	import Provenance from '$lib/community/Provenance.svelte';
	import { articleTarget } from '$lib/community/repo';
	import { byEntryOrder, sourceOf } from '$lib/entities/sources';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const a = $derived(data.article);
	const src = $derived(sourceOf(a.source));
	const sourceName = $derived(`${src.name} (${src.year})`);
	const hasTa = $derived(a.paragraphs.some((p) => p.ta));
	/** This entry and its siblings, in entry order: the source switcher. */
	const sources = $derived(
		byEntryOrder(
			[{ source: a.source, id: a.id }, ...(a.also_in ?? []).map((x) => ({ source: x.source, id: x.id }))],
			(x) => x.source
		)
	);
	/** How many community corrections stand in the Tamil of this entry. */
	const corrections = $derived(a.paragraphs.filter((p) => p.ta_source === 'community' || p.ta_source === 'owner').length);
	const description = $derived((a.paragraphs[0]?.ta ?? a.paragraphs[0]?.text ?? '').slice(0, 160));
</script>

<svelte:head>
	<title>{a.title} · அகராதி · Dictionary · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com/dictionary/${a.id}`} />
	<meta property="og:title" content={a.title} />
	<meta property="og:description" content={description} />
</svelte:head>

<article class="art">
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a> <span aria-hidden="true">›</span>
		<a href="/dictionary?l={a.title[0]?.toUpperCase()}&s={a.source}" lang={ta ? 'ta' : 'en'}>{ta ? 'அகராதி' : 'Dictionary'}</a> <span aria-hidden="true">›</span>
		<span aria-current="page">{a.title}</span>
	</nav>

	<header class="head">
		<div class="kicker">{sourceName} · {ta ? src.licence_ta : src.licence_en} <span class="badge" title={hasTa ? (ta ? 'தமிழ் வரைவு உள்ளது' : 'Tamil draft available') : (ta ? 'ஆங்கிலம் மட்டும்' : 'English only')}>{hasTa ? 'TA' : 'EN'}</span></div>
		<h1>{a.title}{#if a.title_ta} <span class="title-ta" lang="ta">{a.title_ta}</span>{/if}</h1>
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
		{#if sources.length > 1}
			<div class="sources">
				<div class="srow">
					<span class="slabel" lang={ta ? 'ta' : 'en'}>{ta ? 'மூலம் · Source' : 'Source'}</span>
					<span class="scount" lang={ta ? 'ta' : 'en'}>{ta ? `${sources.length} அகராதிகளில்` : `in ${sources.length} dictionaries`}</span>
				</div>
				<div class="pills" role="group" aria-label={ta ? 'அகராதி மூலம்' : 'Dictionary source'}>
					{#each sources as s, i (s.id)}
						{@const so = sourceOf(s.source)}
						{#if s.id === a.id}
							<span class="pill on" aria-current="true">{so.short}{#if i === 0}<span class="def" lang={ta ? 'ta' : 'en'}>{ta ? 'இயல்பு' : 'default'}</span>{/if}</span>
						{:else}
							<a class="pill" href="/dictionary/{s.id}">{so.short}</a>
						{/if}
					{/each}
				</div>
			</div>
		{/if}
	</header>

	<div class="body">
		{#each a.paragraphs as p (p.id)}
			<div class="para" class:heading={p.heading} id={p.id.split('#')[1]}>
				{#if p.heading}
					<h2 lang={p.ta ? 'ta' : 'en'}>{p.ta ?? p.text}</h2>
				{:else if p.ta}
					<p lang="ta" class="ta"><RefText text={p.ta} /></p>
					<details class="src"><summary lang={ta ? 'ta' : 'en'}>{ta ? 'ஆங்கில மூலம்' : 'English source'}</summary><p lang="en"><RefText text={p.text} /></p></details>
					<Provenance kind={p.ta_source ?? 'draft'} lang={ta ? 'ta' : 'en'} />
				{:else}
					<p lang="en"><RefText text={p.text} /></p>
				{/if}
				<SuggestControl target={articleTarget(p.id)} current={p.ta ?? ''} source={p.text} lang={ta ? 'ta' : 'en'} />
			</div>
		{/each}
	</div>

	<div class="prov">
		<div class="pmeta">
			<div class="pname">{src.name}, {src.year}</div>
			<div class="pta" lang={ta ? 'ta' : 'en'}>
				{#if hasTa}
					{ta ? 'தமிழாக்கம்' : 'Tamil translation'}{#if corrections} · <span class="ok">✓ {corrections} {ta ? 'சமூக திருத்தங்கள்' : corrections === 1 ? 'community correction' : 'community corrections'}</span>{/if}
				{:else}
					{ta ? 'தமிழாக்கம் இன்னும் இல்லை' : 'no Tamil translation yet'}
				{/if}
			</div>
		</div>
		<a class="pedit" href="#{a.paragraphs[0]?.id.split('#')[1] ?? ''}" lang={ta ? 'ta' : 'en'}>✎ {ta ? (hasTa ? 'திருத்து' : 'தமிழாக்கம் பரிந்துரை') : hasTa ? 'Suggest a correction' : 'Suggest a translation'}</a>
	</div>

	{#if a.also_in?.length}
		<section class="also">
			<h2 class="alabel" lang={ta ? 'ta' : 'en'}>{ta ? 'மற்ற அகராதிகளில் · Also in' : 'Also in'}</h2>
			<ul>
				{#each a.also_in as s (s.id)}
					{@const so = sourceOf(s.source)}
					<li>
						<a href="/dictionary/{s.id}">
							<div class="atext">
								<div class="ahead">{so.short} <span class="ayear">· {so.year}</span></div>
								<div class="aprev" lang={s.preview_ta ? 'ta' : 'en'}>{s.preview}</div>
							</div>
							<span class="achev" aria-hidden="true">›</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<footer class="foot">
		<p class="source">{a.attribution}</p>
		{#if src.sharealike}<p class="note" lang={ta ? 'ta' : 'en'}>{ta ? 'இக்கட்டுரையின் தமிழ் வடிவங்களும் திருத்தங்களும் CC BY-SA 4.0 உரிமத்திலேயே வெளியிடப்படும்.' : 'Tamil versions and corrections of this article are released under the same CC BY-SA 4.0 licence.'}</p>{/if}
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
	.para h2 { margin: 0.6rem 0 0; font-size: 1.15rem; font-weight: 700; }
	.para h2[lang='ta'] { font-family: var(--tamil); }
	.para p.ta { font-family: var(--tamil); font-size: 1.15rem; line-height: 1.9; }
	.src { margin-top: 0.4rem; font-size: 0.92rem; color: var(--ink-2); }
	.src summary { cursor: pointer; color: var(--muted); font-size: 0.8rem; }
	.src summary[lang='ta'] { font-family: var(--tamil); }
	.src p { margin-top: 0.3rem; font-size: 0.95rem; }
	/* Source switcher: the same headword in the other dictionaries (design 8A). */
	.sources { margin-top: 1rem; display: grid; gap: 0.45rem; }
	.srow { display: flex; align-items: baseline; gap: 0.6rem; }
	.slabel { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
	.slabel[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.78rem; }
	.scount { font-size: 0.78rem; color: var(--muted); }
	.scount[lang='ta'] { font-family: var(--tamil); }
	.pills { display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.pill { display: inline-flex; align-items: center; gap: 0.4rem; min-height: 34px; padding: 0.2rem 0.8rem; border: var(--bw) solid var(--line-2); border-radius: 999px; font-size: 0.88rem; font-weight: 600; color: var(--ink-2); text-decoration: none; }
	.pill:hover { border-color: var(--accent); color: var(--accent); }
	.pill.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.def { font-size: 0.66rem; font-weight: 700; letter-spacing: 0.06em; opacity: 0.8; }
	.def[lang='ta'] { font-family: var(--tamil); letter-spacing: 0; }

	/* Provenance: which dictionary, and what has happened to its Tamil. */
	.prov { margin-top: 1.6rem; display: flex; align-items: center; justify-content: space-between; gap: 0.8rem; flex-wrap: wrap; padding: 0.7rem 0.9rem; border: var(--bw) solid var(--line); border-radius: var(--r); background: var(--surface-2); }
	.pname { font-size: 0.84rem; font-weight: 600; }
	.pta { font-size: 0.78rem; color: var(--muted); margin-top: 0.1rem; }
	.pta[lang='ta'] { font-family: var(--tamil); }
	.ok { color: var(--good); font-weight: 600; }
	.pedit { font-size: 0.85rem; font-weight: 600; text-decoration: none; color: var(--accent); white-space: nowrap; }
	.pedit[lang='ta'] { font-family: var(--tamil); }

	/* One line from each of the other dictionaries. */
	.also { margin-top: 1.2rem; }
	.alabel { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.5rem; }
	.alabel[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.8rem; }
	.also ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.45rem; }
	.also a { display: flex; align-items: center; gap: 0.7rem; padding: 0.65rem 0.85rem; border: var(--bw) solid var(--line); border-radius: var(--r); text-decoration: none; color: inherit; }
	.also a:hover { border-color: var(--accent); }
	.atext { min-width: 0; flex: 1; }
	.ahead { font-size: 0.82rem; font-weight: 700; }
	.ayear { font-weight: 500; color: var(--muted); }
	.aprev { font-size: 0.85rem; color: var(--ink-2); margin-top: 0.1rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.aprev[lang='ta'] { font-family: var(--tamil); }
	.achev { color: var(--muted); flex: none; }

	.title-ta { font-family: var(--tamil); color: var(--muted); font-weight: 500; font-size: 0.7em; margin-left: 0.4em; }
	.foot { margin-top: 2rem; border-top: 1px solid var(--line); padding-top: 0.9rem; display: grid; gap: 0.4rem; }
	.source, .note { margin: 0; font-size: 0.78rem; color: var(--muted); }
	.note[lang='ta'] { font-family: var(--tamil); }
</style>

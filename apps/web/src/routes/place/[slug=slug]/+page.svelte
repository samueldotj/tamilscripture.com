<script lang="ts">
	import { chapterUrl, findBook, manifest } from '$lib/content/manifest';
	import { groupByBook, placeLabelTa } from '$lib/entities/load';
	import { settings } from '$lib/settings/store.svelte';
	import SuggestControl from '$lib/community/SuggestControl.svelte';
	import Provenance from '$lib/community/Provenance.svelte';
	import { nameTarget } from '$lib/community/repo';

	let { data } = $props();
	const ui = $derived(settings.value.uiLang);
	const ta = $derived(ui === 'ta');
	const p = $derived(data.place);
	const labelTa = $derived(placeLabelTa(p));
	const title = $derived(ta && labelTa ? labelTa : p.name_en);
	const alt = $derived(ta ? p.name_en : (labelTa ?? ''));
	const qualifier = $derived(p.qualifier ? ` (${p.qualifier})` : '');
	const version = $derived(settings.value.version);
	const kind = $derived(data.glossary?.types[p.place_type] ?? { ta: p.place_type, en: p.place_type });
	const precision = $derived(data.glossary?.precision[p.geo?.precision ?? 'unlocated'] ?? { ta: '', en: '' });
	const groups = $derived(groupByBook(p.verses));
	const tamilVersions = $derived(manifest.versions.filter((v) => v.lang === 'ta'));
	const description = $derived(
		ta
			? `${title}${qualifier}: வேதாகமத்தில் ${p.verses.length} வசனங்களில் குறிப்பிடப்படும் ${kind.ta}.`
			: `${p.name_en}${qualifier}, a biblical ${kind.en} named in ${p.verses.length} verses.`
	);
	function verseHref(v: string) {
		const [code, ch, n] = v.split('.');
		const book = findBook(code)!;
		return chapterUrl(version, book, Number(ch), n);
	}
	function verseNo(v: string) {
		const [, ch, n] = v.split('.');
		return `${ch}:${n}`;
	}
</script>

<svelte:head>
	<title>{title}{qualifier} · {ta ? 'இடம்' : 'Place'} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com/place/${p.id}`} />
	<meta property="og:title" content={`${title}${qualifier}`} />
	<meta property="og:description" content={description} />
</svelte:head>

<article class="place">
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a> <span aria-hidden="true">›</span>
		<a href="/atlas" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம்' : 'Atlas'}</a> <span aria-hidden="true">›</span>
		<span aria-current="page" lang={ta ? 'ta' : 'en'}>{title}{qualifier}</span>
	</nav>

	<header class="head">
		<div class="kicker"><span lang="ta">{kind.ta}</span> · {kind.en}{#if p.geo && p.geo.precision !== 'point'} · <span lang={ta ? 'ta' : 'en'}>{ta ? precision.ta : precision.en}</span>{/if}</div>
		<div class="titles">
			<h1 lang={ta ? 'ta' : 'en'}>{title}<span class="q">{qualifier}</span></h1>
			{#if alt}<span class="alt" lang={ta ? 'en' : 'ta'}>{alt}</span>{/if}
		</div>
		{#if p.alt_en?.length || p.modern}
			<p class="also">
				{#if p.alt_en?.length}<span><span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'வேறு பெயர்கள்' : 'Also'}:</span> {p.alt_en.join(' · ')}</span>{/if}
				{#if p.modern && p.modern !== p.name_en}<span><span class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'இன்று' : 'Today'}:</span> {p.modern}</span>{/if}
			</p>
		{/if}
	</header>

	<div class="grid">
		<div class="main">
			{#if data.svg}
				<div class="mapwrap">{@html data.svg}</div>
				{#if p.geo}
					<p class="coords">
						<span class="mono">{p.geo.lat.toFixed(3)}°N {p.geo.lon.toFixed(3)}°E</span>
						<a class="chip" href={`/atlas/explore?place=${p.id}`}><span lang="ta">வரைபடத்தில் காண்</span> · Explore map</a>
					</p>
				{/if}
			{:else}
				<p class="unlocated card" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த இடத்தின் அமைவிடம் அறியப்படவில்லை.' : 'The location of this place is not known.'}</p>
			{/if}

			<section class="verses">
				<h2 class="kicker"><span lang="ta">வசனங்கள்</span> · Verses <span class="n">{p.verses.length}</span></h2>
				{#each groups as [code, verses] (code)}
					{@const book = findBook(code)}
					{#if book}
						<div class="book">
							<h3 lang={ta ? 'ta' : 'en'}><a href={chapterUrl(version, book)}>{ta ? book.name_ta : book.name_en}</a></h3>
							<div class="refs">
								{#each verses as v (v)}
									<a href={verseHref(v)}>{verseNo(v)}</a>
								{/each}
							</div>
						</div>
					{/if}
				{/each}
			</section>
		</div>

		<aside class="side">
			<section class="card names">
				<h2 class="kicker"><span lang="ta">தமிழ்ப் பெயர்கள்</span> · Tamil names</h2>
				{#if Object.keys(p.names_ta).length}
					<dl>
						{#each tamilVersions as v (v.code)}
							{@const n = p.names_ta[v.code]}
							{#if n}
								<div>
									<dt>{v.short}</dt>
									<dd>
										<strong lang="ta">{n.label}</strong>
										{#if n.provenance}<Provenance kind={n.provenance} lang={ui} />{:else if n.draft}<Provenance kind="auto" lang={ui} />{/if}
										{#if n.forms.length > 1}<span class="forms" lang="ta">{n.forms.filter((f) => f !== n.label).slice(0, 6).join(' · ')}</span>{/if}
										<SuggestControl target={nameTarget(v.code, p.name_en)} current={n.label} lang={ui} compact />
									</dd>
								</div>
							{:else}
								<div>
									<dt>{v.short}</dt>
									<dd>
										<span class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இல்லை' : 'none yet'}</span>
										<SuggestControl target={nameTarget(v.code, p.name_en)} current="" lang={ui} compact />
									</dd>
								</div>
							{/if}
						{/each}
					</dl>
				{:else}
					<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'தமிழ் வடிவம் இன்னும் இணைக்கப்படவில்லை.' : 'No Tamil form has been aligned yet.'}</p>
					{#each tamilVersions as v (v.code)}
						<SuggestControl target={nameTarget(v.code, p.name_en)} current="" lang={ui} compact />
					{/each}
				{/if}
			</section>

			{#if data.journeys.length}
				<section class="card">
					<h2 class="kicker"><span lang="ta">பயணங்கள்</span> · Journeys</h2>
					<ul class="plain">
						{#each data.journeys as j (j.id)}
							<li><a href="/atlas/{j.id}" lang={ta ? 'ta' : 'en'}>{ta ? j.name_ta : j.name_en}</a></li>
						{/each}
					</ul>
				</section>
			{/if}

			{#if p.nearby?.length}
				<section class="card">
					<h2 class="kicker"><span lang="ta">அருகில்</span> · Nearby</h2>
					<ul class="chips">
						{#each p.nearby as n (n.id)}
							<li><a class="chip round" href="/place/{n.id}" lang={ta && n.name_ta ? 'ta' : 'en'}>{ta && n.name_ta ? n.name_ta : n.name_en}{n.qualifier ? ` (${n.qualifier})` : ''}</a></li>
						{/each}
					</ul>
				</section>
			{/if}

			<p class="source">
				<a href={p.source.url} rel="license">{p.source.attribution}</a>{#if data.svg} · Natural Earth{/if}
			</p>
		</aside>
	</div>
</article>

<style>
	.place { max-width: 74rem; }
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: var(--accent); font-weight: 600; text-decoration: none; }
	.crumbs [lang='ta'] { font-family: var(--tamil); }
	.head { margin-bottom: 1.4rem; }
	.head .kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.titles { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.4rem 0.9rem; margin: 0.3rem 0 0.4rem; }
	h1 { font-size: 2.2rem; font-weight: 600; margin: 0; line-height: 1.2; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	h1 .q { color: var(--muted); font-weight: 400; font-size: 0.6em; margin-left: 0.2em; }
	.alt { font-size: 1rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); }
	.also { margin: 0; color: var(--ink-2); font-size: 0.92rem; display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem; }
	.also .k { color: var(--muted); }
	.also .k[lang='ta'] { font-family: var(--tamil); }
	.grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
	.mapwrap { aspect-ratio: 800 / 480; }
	.mapwrap :global(svg) { width: 100%; height: 100%; }
	.coords { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin: 0.7rem 0 0; font-size: 0.85rem; color: var(--muted); }
	.mono { font-variant-numeric: tabular-nums; }
	.coords .chip [lang='ta'] { font-family: var(--tamil); }
	.unlocated { padding: 1rem 1.2rem; color: var(--muted); margin: 0; }
	.unlocated[lang='ta'] { font-family: var(--tamil); }
	.verses { margin-top: 1.8rem; }
	.verses h2 { margin: 0 0 0.8rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.kicker .n { font-weight: 600; margin-left: 0.3rem; }
	.book { display: grid; grid-template-columns: 11rem minmax(0, 1fr); gap: 0.6rem 1rem; padding: 0.7rem 0; border-top: 1px solid var(--line); align-items: start; }
	.book h3 { margin: 0; font-size: 1rem; font-weight: 600; }
	.book h3[lang='ta'] { font-family: var(--tamil); }
	.book h3 a { text-decoration: none; color: var(--ink); }
	.refs { display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.refs a { padding: 0.15rem 0.5rem; border: 1px solid var(--line); border-radius: var(--r-s); text-decoration: none; font-size: 0.82rem; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--ink-2); background: var(--surface); }
	.refs a:hover { border-color: var(--accent); color: var(--accent); }
	.side { display: grid; gap: 1rem; align-content: start; }
	.card { padding: 1rem 1.2rem; }
	.card h2 { margin: 0 0 0.6rem; }
	dl { margin: 0; display: grid; gap: 0.6rem; }
	dl div { display: grid; grid-template-columns: 3.2rem 1fr; gap: 0.5rem; align-items: baseline; }
	dt { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; color: var(--muted); }
	dd { margin: 0; display: flex; flex-wrap: wrap; gap: 0.3rem 0.6rem; align-items: baseline; }
	dd :global(.suggest) { flex-basis: 100%; }
	dd strong { font-family: var(--tamil); font-size: 1.15rem; }
	.forms { font-family: var(--tamil); font-size: 0.85rem; color: var(--muted); }
	.plain { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
	.plain a { font-weight: 600; text-decoration: none; }
	.plain a[lang='ta'] { font-family: var(--tamil); }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.chips .chip { min-height: 36px; font-weight: 500; font-size: 0.88rem; padding: 0.3rem 0.8rem; }
	.chips .chip[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); margin: 0; }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.source { font-size: 0.75rem; color: var(--muted); margin: 0; }
	.source a { color: inherit; }
	@media (min-width: 900px) {
		.grid { grid-template-columns: minmax(0, 1fr) 20rem; }
	}
	@media (max-width: 560px) {
		.book { grid-template-columns: 1fr; gap: 0.3rem; }
	}
</style>

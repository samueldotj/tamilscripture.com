<script lang="ts">
	import RefText from '$lib/refs/RefText.svelte';
	import { chapterUrl, findBook, manifest } from '$lib/content/manifest';
	import { groupByBook, placeLabelTa } from '$lib/entities/load';
	import { settings } from '$lib/settings/store.svelte';
	import SuggestControl from '$lib/community/SuggestControl.svelte';
	import Provenance from '$lib/community/Provenance.svelte';
	import { nameTarget } from '$lib/community/repo';
	import { sourceOf } from '$lib/entities/sources';

	let { data } = $props();
	const ui = $derived(settings.value.uiLang);
	const ta = $derived(ui === 'ta');
	const p = $derived(data.person);
	const labelTa = $derived(placeLabelTa(p));
	const title = $derived(ta && labelTa ? labelTa : p.name_en);
	const alt = $derived(ta ? p.name_en : (labelTa ?? ''));
	const qualifier = $derived(p.qualifier ? ` (${p.qualifier})` : '');
	const version = $derived(settings.value.version);
	const groups = $derived(groupByBook(p.verses));
	const tamilVersions = $derived(manifest.versions.filter((v) => v.lang === 'ta'));
	const kind = $derived(p.gender === 'group' ? { ta: 'மக்கள் குழு', en: 'People group' } : p.gender === 'female' ? { ta: 'பெண்', en: 'Woman' } : { ta: 'ஆண்', en: 'Man' });
	const relationLabels = { parents: ['பெற்றோர்', 'Parents'], partners: ['துணை', 'Spouse'], siblings: ['உடன்பிறந்தோர்', 'Siblings'], children: ['பிள்ளைகள்', 'Children'] } as const;
	const relationOrder = ['parents', 'partners', 'siblings', 'children'] as const;
	const relations = $derived(relationOrder.filter((k) => p.relations[k]?.length).map((k) => ({ key: k, label: ta ? relationLabels[k][0] : relationLabels[k][1], people: p.relations[k]! })));
	const paragraphs = $derived((p.article ?? '').split(/\n+/).map((s) => s.trim()).filter(Boolean));
	const description = $derived(
		ta
			? `${title}${qualifier}: ${p.brief ?? p.description ?? ''} வேதாகமத்தில் ${p.verses.length} வசனங்களில் குறிப்பிடப்படுகிறார்.`
			: `${p.name_en}${qualifier}: ${p.brief ?? p.description ?? 'a person in the Bible'}, named in ${p.verses.length} verses.`
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
	<title>{labelTa ? `${labelTa} – ` : ''}{p.name_en}{qualifier} · நபர் · Person · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com/person/${p.id}`} />
	<meta property="og:title" content={`${title}${qualifier}`} />
	<meta property="og:description" content={description} />
	{@html `<script type="application/ld+json">${JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'Person',
		name: p.name_en,
		...(labelTa ? { alternateName: labelTa } : {}),
		description,
		url: `https://www.tamilscripture.com/person/${p.id}`
	})}</script>`}
</svelte:head>

<article class="person">
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a> <span aria-hidden="true">›</span>
		<a href="/dictionary" lang={ta ? 'ta' : 'en'}>{ta ? 'அகராதி' : 'Dictionary'}</a> <span aria-hidden="true">›</span>
		<span aria-current="page" lang={ta ? 'ta' : 'en'}>{title}{qualifier}</span>
	</nav>

	<header class="head">
		<div class="kicker"><span lang="ta">{kind.ta}</span> · {kind.en}{#if p.tribe} · {p.tribe}{/if}{#if p.uncertain} · <span lang={ta ? 'ta' : 'en'}>{ta ? 'அடையாளம் உறுதியற்றது' : 'identity uncertain'}</span>{/if}</div>
		<div class="titles">
			<h1 lang={ta ? 'ta' : 'en'}>{title}<span class="q">{qualifier}</span></h1>
			{#if alt}<span class="alt" lang={ta ? 'en' : 'ta'}>{alt}</span>{/if}
		</div>
		{#if p.brief || p.description}
			<p class="brief">{p.brief ?? p.description}</p>
		{/if}
	</header>

	<div class="grid">
		<div class="main">
			{#if p.short || paragraphs.length}
				<section class="about card">
					<h2 class="kicker"><span lang="ta">பற்றி</span> · About</h2>
					{#if p.short && !paragraphs.length}<p><RefText text={p.short} /></p>{/if}
					{#each paragraphs as para, i (i)}
						<p><RefText text={para} /></p>
					{/each}
					<p class="source"><a href={p.source.url} rel="license">{p.source.attribution}</a></p>
				</section>
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

			{#if p.forms.length}
				<section class="card">
					<h2 class="kicker"><span lang="ta">மூல மொழியில்</span> · Original</h2>
					<ul class="plain orig">
						{#each p.forms.slice(0, 6) as f (f.strongs + f.original + f.significance)}
							<li><span lang={f.script} class="orig-word">{f.original}</span> <a class="strongs" href="/strongs/{f.strongs}" title="Every verse this word is used in">{f.strongs}</a>{#if f.translated && f.translated !== p.name_en} <span class="muted">{f.translated}</span>{/if}</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#each relations as r (r.key)}
				<section class="card">
					<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{r.label}</h2>
					<ul class="chips">
						{#each r.people as rel (rel.id)}
							<li><a class="chip round" href="/person/{rel.id}" lang={ta && rel.name_ta ? 'ta' : 'en'} title={rel.brief ?? undefined}>{ta && rel.name_ta ? rel.name_ta : rel.name_en}</a></li>
						{/each}
					</ul>
				</section>
			{/each}

			{#if p.articles?.length}
				<section class="card">
					<h2 class="kicker"><span lang="ta">அகராதி</span> · Dictionary</h2>
					<ul class="plain">
						{#each p.articles as a (a.id)}
							<li><a href="/dictionary/{a.id}">{a.title}</a> <span class="muted small">{sourceOf(a.source).short}</span></li>
						{/each}
					</ul>
				</section>
			{/if}
		</aside>
	</div>
</article>

<style>
	.person { max-width: 74rem; }
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
	.brief { margin: 0; color: var(--ink-2); font-size: 1.05rem; max-width: 40rem; }
	.grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 1.5rem; }
	.about { padding: 1.1rem 1.3rem; }
	.about h2 { margin: 0 0 0.6rem; }
	.about p { margin: 0 0 0.8rem; line-height: 1.7; max-width: 42rem; }
	.about p:last-of-type { margin-bottom: 0; }
	.verses { margin-top: 1.8rem; }
	.verses h2 { margin: 0 0 0.8rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
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
	.orig li { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: baseline; }
	.orig-word { font-size: 1.15rem; }
	.strongs { font-size: 0.72rem; color: var(--accent); letter-spacing: 0.04em; text-decoration: none; }
	.strongs:hover { text-decoration: underline; }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.chips .chip { min-height: 36px; font-weight: 500; font-size: 0.88rem; padding: 0.3rem 0.8rem; }
	.chips .chip[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); margin: 0; }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.small { font-size: 0.78rem; }
	.source { font-size: 0.75rem; color: var(--muted); margin: 0.8rem 0 0 !important; }
	.source a { color: inherit; }
	@media (min-width: 900px) {
		.grid { grid-template-columns: minmax(0, 1fr) 20rem; }
	}
	@media (max-width: 560px) {
		.book { grid-template-columns: 1fr; gap: 0.3rem; }
	}
</style>

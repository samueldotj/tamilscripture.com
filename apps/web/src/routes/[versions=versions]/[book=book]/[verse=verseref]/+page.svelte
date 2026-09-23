<script lang="ts">
	import { bookNameIn, chapterUrl, DEFAULT_VERSION, findVersion, verseUrl } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const b = $derived(data.book);
	const verses = $derived(data.range.start === data.range.end ? `${data.range.start}` : `${data.range.start}-${data.range.end}`);
	const refTa = $derived(`${b.name_ta} ${data.chapter}:${verses}`);
	const refEn = $derived(`${b.name_en} ${data.chapter}:${verses}`);
	const many = $derived(data.range.end > data.range.start);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	const chapterHref = $derived(chapterUrl(versionPath, b, data.chapter));

	// Search engines (ADR-15): one canonical page per passage, the default Tamil version's.
	const seoVersion = $derived(findVersion(DEFAULT_VERSION)?.books.includes(b.code) ? findVersion(DEFAULT_VERSION)! : data.versions[0]);
	const seoUrl = $derived(`https://www.tamilscripture.com${verseUrl(seoVersion.code.toLowerCase(), b, data.chapter, verses)}`);
	const primaryText = $derived(data.shown[0].verses.map((v) => v.text).join(' '));
	const description = $derived(primaryText.length <= 160 ? primaryText : primaryText.slice(0, 160).replace(/\s\S*$/, '') + '…');

	/** Long passages step the type down so a range still fits a screen or two. Sized from
	 *  the longest version (Tamil runs longer), so the versions step down together. */
	const size = $derived.by(() => {
		const len = Math.max(...data.shown.map((s) => s.verses.reduce((n, v) => n + v.text.length, 0)));
		return len < 220 ? 'xl' : len < 600 ? 'l' : 'm';
	});
</script>

<svelte:head>
	<title>{refTa} – {refEn} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={seoUrl} />
	<meta property="og:title" content={`${refTa} – ${refEn}`} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="article" />
	<meta property="og:url" content={seoUrl} />
	<meta property="og:site_name" content="Tamil Scripture · தமிழ் வேதாகமம்" />
	<meta property="og:locale" content={data.shown[0].version.lang === 'ta' ? 'ta_IN' : 'en_IN'} />
	{@html `<script type="application/ld+json">${JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: [
			{ '@type': 'ListItem', position: 1, name: 'தமிழ் வேதாகமம்', item: 'https://www.tamilscripture.com/' },
			{ '@type': 'ListItem', position: 2, name: b.name_ta, item: `https://www.tamilscripture.com${chapterUrl(seoVersion.code.toLowerCase(), b)}` },
			{ '@type': 'ListItem', position: 3, name: `${b.name_ta} ${data.chapter}`, item: `https://www.tamilscripture.com${chapterUrl(seoVersion.code.toLowerCase(), b, data.chapter)}` },
			{ '@type': 'ListItem', position: 4, name: refTa, item: seoUrl }
		]
	})}</script>`}
</svelte:head>

<article class="verse">
	<h1>
		<span lang="ta">{refTa}</span>
		<span class="en" lang="en">{refEn}</span>
	</h1>

	{#each data.shown as s (s.version.code)}
		<figure class="passage {size}" lang={s.version.lang}>
			<blockquote>
				<p>
					{#each s.verses as v, i (v.n)}{#if many}<sup>{v.n}</sup>{/if}{v.text}{#if i < s.verses.length - 1}{' '}{/if}{/each}
				</p>
			</blockquote>
			<figcaption>{bookNameIn(b, s.version)} {data.chapter}:{verses} · <abbr title={s.version.name}>{s.version.short}</abbr></figcaption>
		</figure>
	{/each}

	<a class="expand" href={chapterHref} lang={ta ? 'ta' : 'en'}>
		{ta ? `${b.name_ta} ${data.chapter} முழுவதும் வாசிக்க` : `Read all of ${b.name_en} ${data.chapter}`} <span aria-hidden="true">→</span>
	</a>
</article>

<style>
	.verse { max-width: 46rem; margin: 0 auto; padding: 1.5rem 0 3rem; }
	h1 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.3rem 0.9rem; margin: 0 0 2rem; font-weight: 600; font-size: 1.5rem; line-height: 1.3; }
	h1 [lang='ta'] { font-family: var(--tamil); color: var(--accent); }
	h1 .en { font-family: var(--sans); font-size: 1rem; font-weight: 500; color: var(--muted); }

	.passage { margin: 0 0 2.25rem; }
	.passage blockquote { margin: 0; padding: 0 0 0 1.2rem; border-left: 4px solid var(--accent); }
	.passage p { margin: 0; text-wrap: pretty; color: var(--ink); }
	.passage[lang='ta'] p { font-family: var(--tamil); line-height: 1.7; }
	.passage[lang='en'] p { font-family: var(--en); color: var(--ink-en); line-height: 1.55; }
	.passage sup { font-family: var(--sans); font-size: 0.45em; font-weight: 700; color: var(--muted); margin-right: 0.2em; vertical-align: 0.9em; line-height: 0; }

	/* Type steps down with the passage's length; the second version sits a step smaller. */
	.passage.xl p { font-size: clamp(1.7rem, 1.1rem + 2.6vw, 2.7rem); }
	.passage.l p { font-size: clamp(1.4rem, 1rem + 1.7vw, 2.05rem); }
	.passage.m p { font-size: clamp(1.2rem, 0.95rem + 1vw, 1.55rem); }
	.passage + .passage.xl p { font-size: clamp(1.4rem, 1rem + 1.8vw, 2.1rem); }
	.passage + .passage.l p { font-size: clamp(1.25rem, 0.95rem + 1.2vw, 1.7rem); }
	.passage + .passage.m p { font-size: clamp(1.1rem, 0.9rem + 0.7vw, 1.35rem); }

	figcaption { margin: 0.7rem 0 0 1.45rem; font-family: var(--sans); font-size: 0.85rem; color: var(--muted); }
	.passage[lang='ta'] figcaption { font-family: var(--tamil); }
	figcaption abbr { text-decoration: none; font-family: var(--sans); font-weight: 600; letter-spacing: 0.03em; }

	.expand { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 44px; padding: 0.6rem 1.1rem; border: var(--bw) solid var(--accent); border-radius: var(--r); color: var(--accent); font-weight: 600; text-decoration: none; }
	.expand[lang='ta'] { font-family: var(--tamil); }
	.expand:hover { background: var(--accent); color: var(--on-accent); }
</style>

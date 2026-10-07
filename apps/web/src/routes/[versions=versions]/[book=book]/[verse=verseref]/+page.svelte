<script lang="ts">
	import { bookNameIn, chapterUrl, DEFAULT_VERSION, findVersion, verseUrl } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';
	import CommentaryText from '$lib/commentary/CommentaryText.svelte';
	import { unitLabel } from '$lib/commentary/load';
	import ShareImage from '$lib/reader/ShareImage.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const b = $derived(data.book);
	const verses = $derived(data.range.start === data.range.end ? `${data.range.start}` : `${data.range.start}-${data.range.end}`);
	const refTa = $derived(`${b.name_ta} ${data.chapter}:${verses}`);
	const refEn = $derived(`${b.name_en} ${data.chapter}:${verses}`);
	const many = $derived(data.range.end > data.range.start);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	const chapterHref = $derived(chapterUrl(versionPath, b, data.chapter));
	// With commentary the page is an explanation of the verse: its title and heading say so.
	const explained = $derived(data.commentary.length > 0);
	const headTitle = $derived(explained ? `${refTa} விளக்கம் – Explanation of ${refEn}` : `${refTa} – ${refEn}`);
	/** Where a section a comment is part of can be read whole: the chapter at its verses. */
	function sectionHref([a, z]: [number, number]): string {
		return chapterUrl(versionPath, b, data.chapter, z >= 999 ? `${a}` : `${a}-${z}`);
	}

	// Search engines (ADR-15): one canonical page per passage, the default Tamil version's.
	const seoVersion = $derived(findVersion(DEFAULT_VERSION)?.books.includes(b.code) ? findVersion(DEFAULT_VERSION)! : data.versions[0]);
	const seoUrl = $derived(`https://www.tamilscripture.com${verseUrl(seoVersion.code.toLowerCase(), b, data.chapter, verses)}`);
	const primaryText = $derived(data.shown[0].verses.map((v) => v.text).join(' '));
	/** The first comment in Tamil (else English), for the description: the snippet promises an explanation. */
	const commentLead = $derived.by(() => {
		const paras = data.commentary.flatMap((c) => c.unit.paragraphs.filter((p) => !p.heading && !p.footnote));
		const p = paras.find((x) => x.ta) ?? paras[0];
		return p ? (p.ta ?? p.text) : '';
	});
	function cut(text: string, n: number): string {
		return text.length <= n ? text : text.slice(0, n).replace(/\s\S*$/, '') + '…';
	}
	const description = $derived(commentLead ? `${cut(primaryText, 90)} — ${cut(commentLead, 150)}` : cut(primaryText, 160));
	const navLang = $derived(ta ? 'ta' : 'en');
	function verseLabel(v: { book: typeof b; chapter: number; verse: number }): string {
		return `${ta ? v.book.name_ta : v.book.name_en} ${v.chapter}:${v.verse}`;
	}

	/** Long passages step the type down so a range still fits a screen or two. Sized from
	 *  the longest version (Tamil runs longer), so the versions step down together. */
	const size = $derived.by(() => {
		const len = Math.max(...data.shown.map((s) => s.verses.reduce((n, v) => n + v.text.length, 0)));
		return len < 220 ? 'xl' : len < 600 ? 'l' : 'm';
	});

	// "Share as image": the picker sits under the passage; the reader's share menu links to it (#image).
	const passages = $derived(data.shown.map((s) => ({
		lang: s.version.lang,
		verses: s.verses,
		ref: `${bookNameIn(b, s.version)} ${data.chapter}:${verses} · ${s.version.short}`
	})));
</script>

<svelte:head>
	<title>{headTitle} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={seoUrl} />
	<meta property="og:title" content={headTitle} />
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
		{#if explained}
			<span lang="ta">{refTa} விளக்கம்</span>
			<span class="en" lang="en">Explanation of {refEn}</span>
		{:else}
			<span lang="ta">{refTa}</span>
			<span class="en" lang="en">{refEn}</span>
		{/if}
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

	{#if explained}
		<section class="explain" aria-labelledby="explain-h">
			<h2 id="explain-h" lang={ta ? 'ta' : 'en'}>{ta ? 'விளக்கவுரைகள்' : 'Commentaries'}</h2>
			{#each data.commentary as c (c.unit.id)}
				<article class="comment">
					<header>
						<span class="badge">{c.source.short}</span>
						<h3 lang="en">{c.source.name} <span class="year">({c.source.year})</span></h3>
						{#if many && !c.partOf}<span class="at">{unitLabel(c.unit, data.chapter)}</span>{/if}
					</header>
					{#if c.unit.title && !c.partOf}<div class="title" lang={ta && c.unit.title_ta ? 'ta' : 'en'}>{ta && c.unit.title_ta ? c.unit.title_ta : c.unit.title}</div>{/if}
					<CommentaryText unit={c.unit} lang={ta ? 'ta' : 'en'} {versionPath} />
					{#if c.partOf}
						<a class="whole" href={sectionHref(c.partOf)} lang={ta ? 'ta' : 'en'}>
							{ta ? `${b.name_ta} ${data.chapter}:${c.partOf[0]}${c.partOf[1] < 999 ? `–${c.partOf[1]}` : ''} பகுதியின் முழு விளக்கம்` : `The whole section on ${b.name_en} ${data.chapter}:${c.partOf[0]}${c.partOf[1] < 999 ? `–${c.partOf[1]}` : ''}`} <span aria-hidden="true">→</span>
						</a>
					{/if}
				</article>
			{/each}
		</section>
	{/if}

	<nav class="step" aria-label={ta ? 'வசனங்கள்' : 'Verses'} lang={navLang}>
		{#if data.prevVerse}
			<a rel="prev" href={verseUrl(versionPath, data.prevVerse.book, data.prevVerse.chapter, `${data.prevVerse.verse}`)}><span aria-hidden="true">←</span> {verseLabel(data.prevVerse)}</a>
		{/if}
		{#if data.nextVerse}
			<a rel="next" class="next" href={verseUrl(versionPath, data.nextVerse.book, data.nextVerse.chapter, `${data.nextVerse.verse}`)}>{verseLabel(data.nextVerse)} <span aria-hidden="true">→</span></a>
		{/if}
	</nav>

	<a class="expand" href={chapterHref} lang={ta ? 'ta' : 'en'}>
		{ta ? `${b.name_ta} ${data.chapter} முழுவதும் வாசிக்க` : `Read all of ${b.name_en} ${data.chapter}`} <span aria-hidden="true">→</span>
	</a>

	<ShareImage {passages} version={data.shown[0].version.code} book={b.code} slug={b.slug} chapter={data.chapter} {verses} {ta} />
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

	.explain { margin: 0 0 2.5rem; display: grid; gap: 1.25rem; }
	.explain h2 { margin: 0; font-size: 1.15rem; font-weight: 700; color: var(--ink); }
	.explain h2[lang='ta'] { font-family: var(--tamil); }
	.comment { display: grid; gap: 0.7rem; padding: 1.1rem 1.2rem 1.2rem; border: var(--bw) solid var(--line); border-radius: 14px; background: var(--surface); }
	.comment header { display: flex; align-items: center; gap: 0.6rem; }
	.comment h3 { margin: 0; font-family: var(--sans); font-size: 0.95rem; font-weight: 700; color: var(--ink); }
	.comment .year { font-weight: 400; color: var(--muted); }
	.comment .at { margin-left: auto; font-family: var(--sans); font-size: 0.82rem; font-weight: 700; color: var(--accent); }
	.badge { font-family: var(--sans); font-size: 0.72rem; font-weight: 800; color: var(--on-accent); background: var(--accent); border-radius: 6px; padding: 0.1rem 0.45rem; }
	.comment .title { font-family: var(--sans); font-weight: 700; color: var(--amber); font-size: 0.92rem; }
	.comment .title[lang='ta'] { font-family: var(--tamil); }
	.whole { justify-self: start; font-family: var(--sans); font-size: 0.88rem; font-weight: 600; color: var(--accent); text-decoration: none; }
	.whole[lang='ta'] { font-family: var(--tamil); }
	.whole:hover { text-decoration: underline; }

	.step { display: flex; gap: 0.75rem; margin: 0 0 1.5rem; font-family: var(--sans); font-size: 0.9rem; }
	.step[lang='ta'] { font-family: var(--tamil); }
	.step a { display: inline-flex; align-items: center; gap: 0.4rem; min-height: 44px; color: var(--ink-2); text-decoration: none; }
	.step a:hover { color: var(--accent); }
	.step .next { margin-left: auto; }

	.expand { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 44px; padding: 0.6rem 1.1rem; border: var(--bw) solid var(--accent); border-radius: var(--r); color: var(--accent); font-weight: 600; text-decoration: none; }
	.expand[lang='ta'] { font-family: var(--tamil); }
	.expand:hover { background: var(--accent); color: var(--on-accent); }
</style>

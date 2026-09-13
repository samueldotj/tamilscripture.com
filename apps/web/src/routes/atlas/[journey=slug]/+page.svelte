<script lang="ts">
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	let { data } = $props();
	const ta = $derived(settings.value.uiLang === 'ta');
	const j = $derived(data.journey);
	const version = $derived(settings.value.version);
	const name = $derived(ta ? j.name_ta : j.name_en);
	const summary = $derived(ta ? j.summary_ta : j.summary_en);
	const period = $derived(data.glossary?.periods[j.period]);

	function refLabel(ref: string) {
		const [code, ch, v] = ref.split('.');
		const book = findBook(code);
		return book ? `${ta ? book.name_ta : book.name_en} ${ch}:${v}` : ref;
	}
	function refHref(ref: string) {
		const [code, ch, v] = ref.split('.');
		const book = findBook(code);
		return book ? chapterUrl(version, book, Number(ch), v) : '#';
	}
	function passageLabel(p: string) {
		const [a, b] = p.split('-');
		return b ? `${refLabel(a)} – ${refLabel(b).replace(/^.*?(\d+:\d+)$/, '$1')}` : refLabel(a);
	}
	function passageHref(p: string) {
		const [a, b] = p.split('-');
		const [code, ch, v] = a.split('.');
		const book = findBook(code);
		if (!book) return '#';
		if (!b) return chapterUrl(version, book, Number(ch), v);
		const [, ch2, v2] = b.split('.');
		return ch === ch2 ? chapterUrl(version, book, Number(ch), `${v}-${v2}`) : chapterUrl(version, book, Number(ch));
	}
</script>

<svelte:head>
	<title>{name} · {ta ? 'வரைபடம்' : 'Atlas'} · Tamil Scripture</title>
	<meta name="description" content={j.summary_en ?? j.name_en} />
	<link rel="canonical" href={`https://www.tamilscripture.com/atlas/${j.id}`} />
</svelte:head>

<article class="journey">
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a> <span aria-hidden="true">›</span>
		<a href="/atlas" lang={ta ? 'ta' : 'en'}>{ta ? 'வரைபடம்' : 'Atlas'}</a> <span aria-hidden="true">›</span>
		<span aria-current="page" lang={ta ? 'ta' : 'en'}>{name}</span>
	</nav>

	<header class="head">
		{#if period}<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? period.ta : period.en}</div>{/if}
		<div class="titles">
			<h1 lang={ta ? 'ta' : 'en'}>{name}</h1>
			<span class="alt" lang={ta ? 'en' : 'ta'}>{ta ? j.name_en : j.name_ta}</span>
		</div>
		{#if summary}<p class="lede" lang={ta ? 'ta' : 'en'}>{summary}</p>{/if}
		{#if j.passages.length}
			<p class="passages">
				{#each j.passages as p (p)}
					<a class="chip" href={passageHref(p)} lang={ta ? 'ta' : 'en'}>{passageLabel(p)}</a>
				{/each}
			</p>
		{/if}
	</header>

	{#if data.svg}
		<div class="mapwrap">{@html data.svg}</div>
		<p class="explore"><a class="chip" href={`/atlas/explore?journey=${j.id}`}><span lang="ta">வரைபடத்தில் காண்</span> · Explore map</a></p>
	{/if}

	<section class="stops">
		<h2 class="kicker"><span lang="ta">நிறுத்தங்கள்</span> · Stops <span class="n">{j.stops.length}</span></h2>
		<ol>
			{#each j.stops as s, i (`${i}-${s.place}`)}
				<li>
					<span class="num">{i + 1}</span>
					<div>
						<a class="name" href="/place/{s.place}" lang={ta && s.name_ta ? 'ta' : 'en'}>{ta && s.name_ta ? s.name_ta : s.name_en}</a>
						<span class="alt" lang={ta ? 'en' : 'ta'}>{ta ? s.name_en : (s.name_ta ?? '')}</span>
						{#if s.ref}<a class="ref" href={refHref(s.ref)} lang={ta ? 'ta' : 'en'}>{refLabel(s.ref)}</a>{/if}
						{#if ta ? s.note_ta : s.note_en}<p class="note" lang={ta ? 'ta' : 'en'}>{ta ? s.note_ta : s.note_en}</p>{/if}
					</div>
				</li>
			{/each}
		</ol>
	</section>

	<p class="credit" lang={ta ? 'ta' : 'en'}>{ta ? 'வழிகள் நிறுத்தங்களுக்கு இடையே நேர்கோடுகளாகக் காட்டப்படுகின்றன; இடங்கள் OpenBible.info (CC BY 4.0), நிலப்படம் Natural Earth.' : 'Routes are drawn as straight legs between stops; places from OpenBible.info (CC BY 4.0), base map from Natural Earth.'}</p>
</article>

<style>
	.journey { max-width: 52rem; }
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: var(--accent); font-weight: 600; text-decoration: none; }
	.crumbs [lang='ta'] { font-family: var(--tamil); }
	.head { margin-bottom: 1.2rem; }
	.head .kicker { color: var(--amber); }
	.head .kicker[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.03em; font-size: 0.85rem; }
	.titles { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.4rem 0.9rem; margin: 0.3rem 0 0.5rem; }
	h1 { font-size: 2rem; font-weight: 600; margin: 0; line-height: 1.25; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.alt { font-size: 0.95rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); }
	.lede { color: var(--ink-2); margin: 0 0 0.8rem; line-height: 1.7; max-width: 42rem; }
	.lede[lang='ta'] { font-family: var(--tamil); }
	.passages { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0; }
	.passages .chip { min-height: 38px; font-size: 0.88rem; }
	.passages .chip[lang='ta'] { font-family: var(--tamil); }
	.mapwrap { aspect-ratio: 800 / 520; }
	.mapwrap :global(svg) { width: 100%; height: 100%; }
	.explore { margin: 0.7rem 0 0; }
	.explore .chip [lang='ta'] { font-family: var(--tamil); }
	.stops { margin-top: 1.8rem; }
	.stops h2 { margin: 0 0 0.8rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.kicker .n { font-weight: 600; margin-left: 0.3rem; }
	ol { list-style: none; margin: 0; padding: 0; display: grid; }
	li { display: grid; grid-template-columns: 2rem 1fr; gap: 0.8rem; padding: 0.7rem 0; border-top: 1px solid var(--line); align-items: start; }
	.num { width: 26px; height: 26px; border-radius: 999px; background: var(--accent); color: var(--on-accent); font-size: 0.78rem; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; margin-top: 0.15rem; }
	li div { display: flex; flex-wrap: wrap; gap: 0.3rem 0.7rem; align-items: baseline; }
	.name { font-weight: 700; text-decoration: none; font-size: 1.05rem; }
	.name[lang='ta'] { font-family: var(--tamil); font-size: 1.1rem; }
	.ref { font-size: 0.82rem; color: var(--muted); text-decoration: none; border: 1px solid var(--line); border-radius: 999px; padding: 0.05rem 0.55rem; }
	.ref:hover { color: var(--accent); border-color: var(--accent); }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.note { flex-basis: 100%; margin: 0; color: var(--ink-2); font-size: 0.92rem; }
	.note[lang='ta'] { font-family: var(--tamil); }
	.credit { font-size: 0.75rem; color: var(--muted); margin-top: 1.5rem; line-height: 1.6; }
	.credit[lang='ta'] { font-family: var(--tamil); }
</style>

<script lang="ts">
	import Chapter from '$lib/reader/Chapter.svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';

	let { data } = $props();

	const primary = $derived(data.versions[0]);
	const isTamil = $derived(primary.lang === 'ta');
	const bookName = $derived(isTamil ? data.book.name_ta : data.book.name_en);
	const title = $derived(`${bookName} ${data.chapter} · ${primary.short}`);
	const description = $derived(
		data.chapters[0].blocks
			.flatMap((b) => (b.type === 'para' ? b.segments.map((s) => s.text) : []))
			.join(' ')
			.slice(0, 160)
	);
	const prev = $derived(data.chapters[0].prev);
	const next = $derived(data.chapters[0].next);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	function navUrl(ref: { book: string; chapter: number } | null) {
		if (!ref) return null;
		const b = findBook(ref.book);
		return b ? chapterUrl(versionPath, b, ref.chapter) : null;
	}
	const testamentName = $derived(
		data.book.testament === 'OT'
			? isTamil ? 'பழைய ஏற்பாடு' : 'Old Testament'
			: isTamil ? 'புதிய ஏற்பாடு' : 'New Testament'
	);
</script>

<svelte:head>
	<title>{title} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com${data.canonical}`} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="article" />
</svelte:head>

<nav class="crumbs" aria-label="Breadcrumb">
	<a href="/">Bible</a>
	<span aria-hidden="true">›</span>
	<span>{testamentName}</span>
	<span aria-hidden="true">›</span>
	<a href={chapterUrl(versionPath, data.book, 1)}>{bookName}</a>
	<span aria-hidden="true">›</span>
	<span aria-current="page">{data.chapter}</span>
</nav>

<div class="pager">
	{#if navUrl(prev)}<a href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முந்தைய' : 'Previous'}</a>{:else}<span></span>{/if}
	<span class="version-tag">{data.versions.map((v) => v.short).join(' + ')}</span>
	{#if navUrl(next)}<a href={navUrl(next)} rel="next">{isTamil ? 'அடுத்த' : 'Next'} ›</a>{:else}<span></span>{/if}
</div>

<h1 lang={primary.lang}>{bookName} {data.chapter}</h1>

{#if data.chapters.length === 1}
	<Chapter chapter={data.chapters[0]} lang={primary.lang} />
{:else}
	<div class="dual">
		{#each data.chapters as ch, i (ch.version)}
			<section aria-label={data.versions[i].name}>
				<h2 class="version-head">{data.versions[i].short}</h2>
				<Chapter chapter={ch} lang={data.versions[i].lang} />
			</section>
		{/each}
	</div>
{/if}

<div class="pager bottom">
	{#if navUrl(prev)}<a href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முந்தைய' : 'Previous'}</a>{:else}<span></span>{/if}
	<span></span>
	{#if navUrl(next)}<a href={navUrl(next)} rel="next">{isTamil ? 'அடுத்த' : 'Next'} ›</a>{:else}<span></span>{/if}
</div>

<footer class="attribution">
	{#each data.versions as v (v.code)}
		<p><a href={v.source_url} rel="license">{v.attribution}</a></p>
	{/each}
</footer>

<style>
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.9rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: inherit; }
	.pager { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 1rem; margin: 0 0 1rem; }
	.pager a:last-child { text-align: right; }
	.pager.bottom { margin-top: 2rem; }
	.version-tag { font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	h1 { font-family: var(--serif); font-weight: 600; font-size: 1.8rem; margin: 0 0 1rem; }
	.dual { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
	@media (max-width: 720px) { .dual { grid-template-columns: 1fr; } }
	.version-head { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.5rem; }
	.attribution { margin-top: 3rem; font-size: 0.8rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 1rem; }
	.attribution a { color: inherit; }
</style>

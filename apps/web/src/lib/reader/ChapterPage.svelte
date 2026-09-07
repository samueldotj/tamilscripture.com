<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import Chapter from './Chapter.svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import type { ChapterPageData } from '$lib/content/chapter-load';

	let { data }: { data: ChapterPageData } = $props();

	const primary = $derived(data.versions[0]);
	const isTamil = $derived(primary.lang === 'ta');
	const bookName = $derived(isTamil ? data.book.name_ta : data.book.name_en);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	const refLabel = $derived(
		data.range
			? `${bookName} ${data.chapter}:${data.range.start}${data.range.end !== data.range.start ? `-${data.range.end}` : ''}`
			: `${bookName} ${data.chapter}`
	);
	const title = $derived(`${refLabel} · ${primary.short}`);

	// Description: the selected verses if any, else the chapter opening.
	const description = $derived.by(() => {
		const segs = data.chapters[0].blocks.flatMap((b) => (b.type === 'para' ? b.segments : []));
		const picked = data.range
			? segs.filter((s) => {
					const n = Number(s.id?.split('.')[2]);
					return n >= data.range!.start && n <= data.range!.end;
				})
			: segs;
		return picked.map((s) => s.text).join(' ').slice(0, 200);
	});

	const prev = $derived(data.chapters[0].prev);
	const next = $derived(data.chapters[0].next);
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

	// Verse ids selected by the URL, e.g. JHN.3.16..18, resolving bridges.
	const selected = $derived.by(() => {
		if (!data.range) return new Set<string>();
		const ids = new Set<string>();
		const bridges = data.chapters[0].bridges ?? {};
		for (let v = data.range.start; v <= data.range.end; v++) {
			const id = `${data.book.code}.${data.chapter}.${v}`;
			ids.add(bridges[id] ?? id);
		}
		return ids;
	});

	afterNavigate(() => {
		if (!data.range) return;
		const first = document.getElementById(`${data.book.code}.${data.chapter}.${data.range.start}`)
			?? document.querySelector(`[data-verse="${[...selected][0]}"]`);
		first?.scrollIntoView({ block: 'start' });
	});
</script>

<svelte:head>
	<title>{title} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com${data.canonical}`} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="article" />
	<meta property="og:url" content={`https://www.tamilscripture.com${data.canonical}`} />
</svelte:head>

<nav class="crumbs" aria-label="Breadcrumb">
	<a href="/">Bible</a>
	<span aria-hidden="true">›</span>
	<span>{testamentName}</span>
	<span aria-hidden="true">›</span>
	<a href={chapterUrl(versionPath, data.book)}>{bookName}</a>
	<span aria-hidden="true">›</span>
	{#if data.range}
		<a href={chapterUrl(versionPath, data.book, data.chapter)}>{data.chapter}</a>
		<span aria-hidden="true">›</span>
		<span aria-current="page">{data.range.start}{data.range.end !== data.range.start ? `-${data.range.end}` : ''}</span>
	{:else}
		<span aria-current="page">{data.chapter}</span>
	{/if}
</nav>

<div class="pager">
	{#if navUrl(prev)}<a href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முந்தைய' : 'Previous'}</a>{:else}<span></span>{/if}
	<span class="version-tag">{data.versions.map((v) => v.short).join(' + ')}</span>
	{#if navUrl(next)}<a href={navUrl(next)} rel="next">{isTamil ? 'அடுத்த' : 'Next'} ›</a>{:else}<span></span>{/if}
</div>

<h1 lang={primary.lang}>{bookName} {data.chapter}</h1>

{#if data.chapters.length === 1}
	<Chapter chapter={data.chapters[0]} lang={primary.lang} {selected} />
{:else}
	<div class="dual">
		{#each data.chapters as ch, i (ch.version)}
			<section aria-label={data.versions[i].name}>
				<h2 class="version-head">{data.versions[i].short}</h2>
				<Chapter chapter={ch} lang={data.versions[i].lang} {selected} />
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
	h1[lang='ta'] { font-family: var(--tamil); }
	.dual { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
	@media (max-width: 720px) { .dual { grid-template-columns: 1fr; } }
	.version-head { font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.5rem; }
	.attribution { margin-top: 3rem; font-size: 0.8rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 1rem; }
	.attribution a { color: inherit; }
</style>

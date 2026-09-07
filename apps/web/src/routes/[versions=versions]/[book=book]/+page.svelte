<script lang="ts">
	import { chapterUrl } from '$lib/content/manifest';

	let { data } = $props();
	const primary = $derived(data.versions[0]);
	const isTamil = $derived(primary.lang === 'ta');
	const bookName = $derived(isTamil ? data.book.name_ta : data.book.name_en);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	const chapters = $derived(Array.from({ length: data.book.chapters }, (_, i) => i + 1));
</script>

<svelte:head>
	<title>{bookName} · {primary.short} · Tamil Scripture</title>
	<link rel="canonical" href={`https://www.tamilscripture.com${data.canonical}`} />
	<meta name="description" content={`${bookName}: ${data.book.chapters} ${isTamil ? 'அதிகாரங்கள்' : 'chapters'} · ${primary.name}`} />
</svelte:head>

<nav class="crumbs" aria-label="Breadcrumb">
	<a href="/">Bible</a> <span aria-hidden="true">›</span>
	<span>{data.book.testament === 'OT' ? (isTamil ? 'பழைய ஏற்பாடு' : 'Old Testament') : (isTamil ? 'புதிய ஏற்பாடு' : 'New Testament')}</span>
	<span aria-hidden="true">›</span> <span aria-current="page">{bookName}</span>
</nav>

<h1 lang={primary.lang}>{bookName} <span class="alt" lang={isTamil ? 'en' : 'ta'}>{isTamil ? data.book.name_en : data.book.name_ta}</span></h1>

<ol class="grid" aria-label={isTamil ? 'அதிகாரங்கள்' : 'Chapters'}>
	{#each chapters as c (c)}
		<li><a href={chapterUrl(versionPath, data.book, c)}>{c}</a></li>
	{/each}
</ol>

{#if data.intro}
	<section class="intro" lang={primary.lang}>
		<h2>{isTamil ? 'முன்னுரை' : 'Introduction'}</h2>
		{#each data.intro.blocks as b, i (i)}
			{#if b.style.startsWith('is') || b.style === 'iot'}
				<h3>{b.text}</h3>
			{:else if b.style.startsWith('io')}
				<p class="outline">{b.text}</p>
			{:else}
				<p>{b.text}</p>
			{/if}
		{/each}
	</section>
{/if}

<style>
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.9rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: inherit; }
	h1 { font-family: var(--serif); font-weight: 600; font-size: 1.8rem; margin: 0 0 1rem; }
	h1[lang='ta'] { font-family: var(--tamil); }
	h1 .alt { font-family: var(--sans); font-weight: 400; font-size: 1rem; color: var(--muted); margin-left: 0.5rem; }
	.grid { list-style: none; padding: 0; margin: 0 0 2rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(3rem, 1fr)); gap: 0.4rem; max-width: 42rem; }
	.grid a { display: block; text-align: center; padding: 0.55rem 0; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); text-decoration: none; font-variant-numeric: tabular-nums; min-height: 44px; line-height: 1.6; }
	.grid a:hover { border-color: var(--accent); }
	.intro { max-width: 42rem; }
	.intro[lang='ta'] { font-family: var(--tamil); line-height: 1.9; }
	.intro h2 { font-family: var(--sans); font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
	.intro h3 { font-size: 1.05rem; margin: 1.2em 0 0.4em; }
	.intro .outline { margin: 0 0 0.2em 1.5em; }
</style>

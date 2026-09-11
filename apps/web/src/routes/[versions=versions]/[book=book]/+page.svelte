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

<div class="book">
	<nav class="crumbs" aria-label="Breadcrumb">
		<a href="/">Bible</a> <span aria-hidden="true">›</span>
		<span>{data.book.testament === 'OT' ? (isTamil ? 'பழைய ஏற்பாடு' : 'Old Testament') : (isTamil ? 'புதிய ஏற்பாடு' : 'New Testament')}</span>
		<span aria-hidden="true">›</span> <span aria-current="page" lang={primary.lang}>{bookName}</span>
	</nav>

	<div class="titles">
		<h1 lang={primary.lang}>{bookName}</h1>
		<span class="alt" lang={isTamil ? 'en' : 'ta'}>{isTamil ? data.book.name_en : data.book.name_ta} · {data.book.chapters} {isTamil ? 'அதிகாரங்கள்' : 'chapters'}</span>
	</div>

	<h2 class="kicker"><span lang="ta">அதிகாரங்கள்</span> · Chapters</h2>
	<ol class="grid" aria-label={isTamil ? 'அதிகாரங்கள்' : 'Chapters'}>
		{#each chapters as c (c)}
			<li><a href={chapterUrl(versionPath, data.book, c)}>{c}</a></li>
		{/each}
	</ol>

	{#if data.intro}
		<section class="intro card" lang={primary.lang}>
			<h2 class="kicker">{isTamil ? 'முன்னுரை' : 'Introduction'}</h2>
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
</div>

<style>
	.book { max-width: 44rem; }
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: var(--accent); font-weight: 600; text-decoration: none; }
	.crumbs [lang='ta'] { font-family: var(--tamil); }
	.titles { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.4rem 0.9rem; margin: 0 0 1.4rem; }
	h1 { font-family: var(--sans); font-weight: 600; font-size: 2.2rem; margin: 0; line-height: 1.2; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.alt { font-size: 0.9rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); }
	h2.kicker { margin: 0 0 0.7rem; }
	h2.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.grid { list-style: none; padding: 0; margin: 0 0 2rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(3.2rem, 1fr)); gap: 0.45rem; }
	.grid a { display: block; text-align: center; padding: 0.6rem 0; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); color: var(--ink-2); text-decoration: none; font-weight: 600; font-size: 0.92rem; font-variant-numeric: tabular-nums; min-height: 44px; line-height: 1.6; }
	.grid a:hover { border-color: var(--accent); background: var(--accent); color: var(--on-accent); }
	.intro { padding: 1.25rem 1.4rem; line-height: 1.75; }
	.intro[lang='ta'] { font-family: var(--tamil); line-height: 1.9; font-size: 1.08rem; }
	.intro h2 { font-family: var(--sans); margin: 0 0 0.6rem; }
	.intro[lang='ta'] h2 { font-family: var(--tamil); letter-spacing: 0.04em; text-transform: none; font-size: 0.9rem; }
	.intro h3 { font-size: 1.05rem; margin: 1.2em 0 0.4em; color: var(--amber); }
	.intro p { margin: 0 0 0.8em; }
	.intro .outline { margin: 0 0 0.2em 1.5em; }
</style>

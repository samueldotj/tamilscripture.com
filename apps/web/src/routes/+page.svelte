<script lang="ts">
	import { chapterUrl, DEFAULT_VERSION, manifest } from '$lib/content/manifest';

	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');
	const version = DEFAULT_VERSION.toLowerCase();
</script>

<svelte:head>
	<title>Tamil Scripture · தமிழ் வேதாகமம்</title>
	<meta name="description" content="Read the Bible in Tamil (IRV, TCV) and English (BSB, WEB, KJV). Fast, free, shareable links to every verse." />
	<link rel="canonical" href="https://www.tamilscripture.com/" />
</svelte:head>

<h1 lang="ta">தமிழ் வேதாகமம்</h1>
<p class="lede">Tamil Bible online. Pick a book to start reading, or open a link like <code>/irvtam/john/3/16</code>.</p>

<section class="versions">
	{#each manifest.versions as v (v.code)}
		<a class="version" href={chapterUrl(v.code.toLowerCase(), manifest.books[0], 1)}>
			<span class="code">{v.short}</span>
			<span class="name" lang={v.lang}>{v.name_native}</span>
		</a>
	{/each}
</section>

<section class="books">
	<h2 lang="ta">பழைய ஏற்பாடு <span class="en">Old Testament</span></h2>
	<ul>
		{#each ot as b (b.code)}
			<li><a href={chapterUrl(version, b, 1)} lang="ta">{b.name_ta}</a> <span class="en">{b.name_en}</span></li>
		{/each}
	</ul>
	<h2 lang="ta">புதிய ஏற்பாடு <span class="en">New Testament</span></h2>
	<ul>
		{#each nt as b (b.code)}
			<li><a href={chapterUrl(version, b, 1)} lang="ta">{b.name_ta}</a> <span class="en">{b.name_en}</span></li>
		{/each}
	</ul>
</section>

<style>
	h1 { font-family: var(--tamil); font-size: 2rem; margin: 0 0 0.5rem; }
	.lede { color: var(--muted); max-width: 40rem; }
	.versions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1.5rem 0 2rem; }
	.version { display: grid; gap: 0.15rem; padding: 0.6rem 0.9rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); text-decoration: none; color: inherit; min-width: 9rem; }
	.version .code { font-size: 0.75rem; letter-spacing: 0.08em; color: var(--accent); font-weight: 600; }
	.version .name { font-size: 0.95rem; }
	.books h2 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
	.books .en { font-family: var(--sans); font-size: 0.8rem; color: var(--muted); font-weight: 400; }
	.books ul { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); gap: 0.25rem 1rem; }
	.books li a { font-family: var(--tamil); text-decoration: none; }
</style>

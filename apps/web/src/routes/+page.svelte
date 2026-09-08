<script lang="ts">
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');
	// Default version comes from settings (changeable in the settings panel or the reader picker).
	const version = $derived(settings.value.version);
	const ta = $derived(settings.value.uiLang === 'ta');
</script>

<svelte:head>
	<title>Tamil Scripture · தமிழ் வேதாகமம்</title>
	<meta name="description" content="Read the Bible in Tamil (IRV, TCV) and English (BSB, WEB, KJV). Fast, free, shareable links to every verse." />
	<link rel="canonical" href="https://www.tamilscripture.com/" />
</svelte:head>

<h1 lang="ta">தமிழ் வேதாகமம்</h1>
<p class="lede">{ta ? 'வாசிக்கத் தொடங்க ஒரு புத்தகத்தைத் தேர்வு செய்யுங்கள், அல்லது மேலே யோவா 3:16 போல தட்டச்சு செய்யுங்கள்.' : 'Pick a book to start reading, or type a reference like John 3:16 above.'}</p>

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
	.lede { color: var(--muted); max-width: 40rem; font-family: var(--tamil); margin-bottom: 1.5rem; }
	.books h2 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }
	.books .en { font-family: var(--sans); font-size: 0.8rem; color: var(--muted); font-weight: 400; }
	.books ul { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); gap: 0.25rem 1rem; }
	.books li a { font-family: var(--tamil); text-decoration: none; }
</style>

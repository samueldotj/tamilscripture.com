<script lang="ts">
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');
	// Default version comes from settings (changeable in the settings panel or the reader picker).
	const version = $derived(settings.value.version);
	const ta = $derived(settings.value.uiLang === 'ta');
	let testament = $state<'OT' | 'NT'>('OT');
</script>

<svelte:head>
	<title>Tamil Scripture · தமிழ் வேதாகமம்</title>
	<meta name="description" content="Read the Bible in Tamil (IRV, TCV) and English (BSB, WEB, KJV). Fast, free, shareable links to every verse." />
	<link rel="canonical" href="https://www.tamilscripture.com/" />
</svelte:head>

<section class="hero">
	<h1 lang="ta">தமிழ் வேதாகமம்</h1>
	<p class="lede" lang={ta ? 'ta' : 'en'}>{ta ? 'வாசிக்கத் தொடங்க ஒரு புத்தகத்தைத் தேர்வு செய்யுங்கள், அல்லது மேலே யோவான் 3:16 போல தட்டச்சு செய்யுங்கள்.' : 'Pick a book to start reading, or type a reference like John 3:16 above.'}</p>
</section>

<div class="seg" role="tablist" aria-label={ta ? 'ஏற்பாடு' : 'Testament'}>
	<button type="button" role="tab" id="tab-ot" aria-selected={testament === 'OT'} aria-controls="books-ot" class:on={testament === 'OT'} onclick={() => (testament = 'OT')}>
		<span lang="ta">பழைய ஏற்பாடு</span> <span class="short">OT</span>
	</button>
	<button type="button" role="tab" id="tab-nt" aria-selected={testament === 'NT'} aria-controls="books-nt" class:on={testament === 'NT'} onclick={() => (testament = 'NT')}>
		<span lang="ta">புதிய ஏற்பாடு</span> <span class="short">NT</span>
	</button>
</div>

<div id="books-ot" role="tabpanel" aria-labelledby="tab-ot" hidden={testament !== 'OT'}>
	<ul class="books">
		{#each ot as b (b.code)}
			<li>
				<a class="book" href={chapterUrl(version, b, 1)}>
					<span class="name" lang={ta ? 'ta' : 'en'}>{ta ? b.name_ta : b.name_en}</span>
					<span class="meta" lang={ta ? 'en' : 'ta'}>{ta ? b.name_en : b.name_ta} · {b.chapters}</span>
				</a>
			</li>
		{/each}
	</ul>
</div>
<div id="books-nt" role="tabpanel" aria-labelledby="tab-nt" hidden={testament !== 'NT'}>
	<ul class="books">
		{#each nt as b (b.code)}
			<li>
				<a class="book" href={chapterUrl(version, b, 1)}>
					<span class="name" lang={ta ? 'ta' : 'en'}>{ta ? b.name_ta : b.name_en}</span>
					<span class="meta" lang={ta ? 'en' : 'ta'}>{ta ? b.name_en : b.name_ta} · {b.chapters}</span>
				</a>
			</li>
		{/each}
	</ul>
</div>

<style>
	.hero { margin: 0.5rem 0 1.5rem; }
	h1 { font-family: var(--tamil); font-size: 2.2rem; font-weight: 600; margin: 0 0 0.4rem; letter-spacing: -0.01em; }
	.lede { color: var(--ink-2); max-width: 40rem; margin: 0; font-size: 1.02rem; line-height: 1.65; }
	.lede[lang='ta'] { font-family: var(--tamil); }
	.seg { display: flex; gap: 0.5rem; background: var(--surface-3); border-radius: 14px; padding: 5px; max-width: 30rem; margin: 0 0 1.2rem; }
	.seg button { flex: 1; border: 0; border-radius: 10px; padding: 0.7rem 0.4rem; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.95rem; cursor: pointer; min-height: 48px; }
	.seg button [lang='ta'] { font-family: var(--tamil); }
	.seg button .short { font-weight: 500; color: var(--muted); }
	.seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.books { list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(11.5rem, 1fr)); gap: 0.65rem; }
	.book { display: flex; flex-direction: column; justify-content: center; gap: 0.1rem; min-height: 4rem; padding: 0.8rem 1rem; border: var(--bw) solid var(--line); border-radius: 14px; background: var(--surface); text-decoration: none; color: inherit; }
	.book:hover { border-color: var(--accent); color: inherit; }
	.book .name { font-size: 1.12rem; font-weight: 600; line-height: 1.3; }
	.book .name[lang='ta'] { font-family: var(--tamil); }
	.book .meta { font-size: 0.76rem; color: var(--muted); }
	.book .meta[lang='ta'] { font-family: var(--tamil); }
	@media (max-width: 480px) {
		.books { grid-template-columns: 1fr 1fr; gap: 0.6rem; }
		.book { padding: 0.75rem 0.9rem; }
	}
</style>

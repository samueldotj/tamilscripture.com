<script lang="ts">
	import { page } from '$app/state';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	const missing = $derived(page.status === 404);
	const version = $derived(settings.value.version);
	// A way back into the text rather than a dead end.
	const starts = $derived(
		[
			{ book: 'JHN', chapter: 3, verse: '16', ta: 'யோவான் 3:16', en: 'John 3:16' },
			{ book: 'PSA', chapter: 23, ta: 'சங்கீதம் 23', en: 'Psalm 23' },
			{ book: 'GEN', chapter: 1, ta: 'ஆதியாகமம் 1', en: 'Genesis 1' }
		].flatMap((s) => {
			const book = findBook(s.book);
			return book ? [{ ...s, href: chapterUrl(version, book, s.chapter, s.verse) }] : [];
		})
	);
</script>

<svelte:head>
	<title>{missing ? 'பக்கம் இல்லை · Page not found' : 'பிழை · Error'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<article class="error">
	<p class="kicker">{page.status}</p>
	<h1 lang={ta ? 'ta' : 'en'}>
		{#if missing}{ta ? 'இந்தப் பக்கம் இல்லை' : 'This page does not exist'}{:else}{ta ? 'ஏதோ தவறு நடந்தது' : 'Something went wrong'}{/if}
	</h1>
	<p class="lede" lang={ta ? 'ta' : 'en'}>
		{#if missing}
			{ta ? 'இணைப்பு தவறாக இருக்கலாம், அல்லது பக்கம் நகர்த்தப்பட்டிருக்கலாம். மேலே யோவான் 3:16 போல ஒரு வசனக் குறிப்பைத் தட்டச்சு செய்யுங்கள், அல்லது கீழே ஒன்றைத் தேர்ந்தெடுங்கள்.' : 'The link may be wrong, or the page may have moved. Type a reference like John 3:16 above, or pick one below.'}
		{:else}
			{ta ? 'சிறிது நேரம் கழித்து மீண்டும் முயலுங்கள்.' : 'Please try again in a moment.'}
		{/if}
	</p>

	<ul class="starts">
		<li><a href="/" lang={ta ? 'ta' : 'en'}>{ta ? 'புத்தகங்கள்' : 'All books'}</a></li>
		{#each starts as s (s.href)}
			<li><a href={s.href} lang={ta ? 'ta' : 'en'}>{ta ? s.ta : s.en}</a></li>
		{/each}
		<li><a href="/search" lang={ta ? 'ta' : 'en'}>{ta ? 'தேடல்' : 'Search'}</a></li>
	</ul>
</article>

<style>
	.error { max-width: 40rem; padding: 2rem 0; }
	.kicker { margin: 0 0 0.4rem; }
	h1 { font-family: var(--sans); font-weight: 600; font-size: 2rem; margin: 0 0 0.8rem; line-height: 1.25; }
	h1[lang='ta'], .lede[lang='ta'], .starts a[lang='ta'] { font-family: var(--tamil); }
	.lede { color: var(--ink-2); line-height: 1.7; margin: 0 0 1.5rem; }
	.starts { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.starts a { display: inline-block; padding: 0.55rem 0.95rem; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); color: var(--ink-2); text-decoration: none; font-weight: 600; min-height: 44px; line-height: 1.6; }
	.starts a:hover { border-color: var(--accent); background: var(--accent); color: var(--on-accent); }
</style>

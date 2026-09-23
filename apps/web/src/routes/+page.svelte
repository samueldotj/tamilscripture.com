<script lang="ts">
	import { onMount } from 'svelte';
	import { bookNameIn, chapterUrl, findBook, findVersion, manifest } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';
	import { session } from '$lib/supabase/session.svelte';
	import { loadLastRead } from '$lib/personal/last-read';
	import type { Book, VersionMeta } from '$lib/content/types';
	import type { TopHighlight } from './api/top-highlights/+server';

	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');
	// Default version comes from settings (changeable in the settings panel or the reader picker).
	const version = $derived(settings.value.version);
	const ta = $derived(settings.value.uiLang === 'ta');
	let testament = $state<'OT' | 'NT'>('OT');
	// "Tamil (IRV, TCV) and English (BSB, WEB, KJV)", from the versions themselves.
	const byLanguage = [...new Set(manifest.versions.map((v) => v.language ?? v.lang))].map(
		(l) => `${l} (${manifest.versions.filter((v) => (v.language ?? v.lang) === l).map((v) => v.short).join(', ')})`
	);
	const blurb = `Read the Bible in ${byLanguage.length > 1 ? `${byLanguage.slice(0, -1).join(', ')} and ${byLanguage.at(-1)}` : byLanguage[0]}. Fast, free, shareable links to every verse.`;

	// "Continue reading" (R-10.6): the passage last opened in this browser, or,
	// for a signed-in reader new to this browser, the latest entry of their history.
	let resume = $state<{ book: Book; chapter: number; versions: VersionMeta[]; href: string } | null>(null);
	function toResume(versionsPath: string, bookCode: string, chapter: number) {
		const book = findBook(bookCode);
		const versions = versionsPath.split('+').map((c) => findVersion(c));
		if (!book || chapter < 1 || chapter > book.chapters || !versions.length || versions.some((v) => !v || !v.books.includes(book.code))) return null;
		return { book, chapter, versions: versions as VersionMeta[], href: chapterUrl(versionsPath, book, chapter) };
	}
	onMount(() => {
		const local = loadLastRead();
		if (local) resume = toResume(local.versions, local.book, local.chapter);
		loadTop();
	});

	// "Most highlighted this month" (R-2.5): the community's ten, with their text
	// in the reader's version. Hidden until at least one verse has three readers.
	let top = $state<(TopHighlight & { book_: Book; text: string })[]>([]);
	const topVersion = $derived(findVersion(version.split('+')[0]) ?? manifest.versions[0]);
	async function loadTop() {
		try {
			const rows = (await (await fetch('/api/top-highlights')).json()) as TopHighlight[];
			if (!Array.isArray(rows) || !rows.length) return;
			const v = topVersion;
			const ids = rows.map((r) => `${r.book}.${r.chapter}.${r.verse}`);
			const texts = (await (await fetch(`/api/verses?${new URLSearchParams({ v: v.code, ids: ids.join(',') })}`)).json()) as Record<string, string>;
			top = rows.flatMap((r, i) => {
				const book_ = findBook(r.book);
				return book_ ? [{ ...r, book_, text: texts[ids[i]] ?? '' }] : [];
			});
		} catch { /* offline, or nothing yet */ }
	}
	$effect(() => {
		if (resume || !session.ready || !session.signedIn) return;
		import('$lib/personal/repo')
			.then(({ history }) => history(1))
			.then(([v]) => { if (v && !resume) resume = toResume(v.version.toLowerCase(), v.book, v.chapter); })
			.catch(() => {});
	});
</script>

<svelte:head>
	<title>Tamil Scripture · தமிழ் வேதாகமம்</title>
	<meta name="description" content={blurb} />
	<link rel="canonical" href="https://www.tamilscripture.com/" />
	<meta property="og:title" content="Tamil Scripture · தமிழ் வேதாகமம்" />
	<meta property="og:description" content={blurb} />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="https://www.tamilscripture.com/" />
	<meta property="og:site_name" content="Tamil Scripture · தமிழ் வேதாகமம்" />
	<meta property="og:locale" content="ta_IN" />
	<!-- WebSite names the site in search results; SearchAction describes /search. -->
	{@html `<script type="application/ld+json">${JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'WebSite',
		name: 'Tamil Scripture',
		alternateName: ['தமிழ் வேதாகமம்', 'TamilScripture.com'],
		url: 'https://www.tamilscripture.com/',
		inLanguage: ['ta', 'en'],
		potentialAction: {
			'@type': 'SearchAction',
			target: { '@type': 'EntryPoint', urlTemplate: 'https://www.tamilscripture.com/search?q={search_term_string}' },
			'query-input': 'required name=search_term_string'
		}
	})}</script>`}
</svelte:head>

<section class="hero">
	<h1 lang="ta">தமிழ் வேதாகமம்</h1>
	<p class="lede" lang={ta ? 'ta' : 'en'}>{ta ? 'வாசிக்கத் தொடங்க ஒரு புத்தகத்தைத் தேர்வு செய்யுங்கள், அல்லது மேலே யோவான் 3:16 போல தட்டச்சு செய்யுங்கள்.' : 'Pick a book to start reading, or type a reference like John 3:16 above.'}</p>
</section>

{#if resume}
	<a class="resume" href={resume.href}>
		<span class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்ந்து வாசிக்க' : 'Continue reading'}</span>
		<span class="ref">
			<span lang={resume.versions[0].lang}>{bookNameIn(resume.book, resume.versions[0])} {resume.chapter}</span>
			<span class="ver">{resume.versions.map((v) => v.short).join(' + ')}</span>
		</span>
		<span class="go" aria-hidden="true">→</span>
	</a>
{/if}

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

{#if top.length}
	<section class="top" aria-labelledby="top-h">
		<h2 id="top-h" class="kicker"><span lang="ta">இந்த மாதம் அதிகம் அடிக்கோடிட்டவை</span> · Most highlighted this month</h2>
		<ol>
			{#each top as t (`${t.book}.${t.chapter}.${t.verse}`)}
				<li>
					<a href={chapterUrl(version.split('+')[0], t.book_, t.chapter, `${t.verse}`)}>
						<span class="ref" lang={topVersion.lang}>{bookNameIn(t.book_, topVersion)} {t.chapter}:{t.verse}</span>
						<span class="users" title={ta ? `${t.users} வாசகர்கள்` : `${t.users} readers`}>◉ {t.users}</span>
						{#if t.text}<span class="text" lang={topVersion.lang}>{t.text}</span>{/if}
					</a>
				</li>
			{/each}
		</ol>
	</section>
{/if}

<style>
	.hero { margin: 0.5rem 0 1.5rem; }
	h1 { font-family: var(--tamil); font-size: 2.2rem; font-weight: 600; margin: 0 0 0.4rem; letter-spacing: -0.01em; }
	.lede { color: var(--ink-2); max-width: 40rem; margin: 0; font-size: 1.02rem; line-height: 1.65; }
	.lede[lang='ta'] { font-family: var(--tamil); }
	.resume { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 0.15rem 1rem; max-width: 30rem; margin: 0 0 1.4rem; padding: 0.8rem 1.1rem; border: var(--bw) solid var(--accent); border-radius: 14px; background: var(--accent-soft); color: inherit; text-decoration: none; }
	.resume:hover { background: var(--surface); color: inherit; }
	.resume .kicker { grid-column: 1; margin: 0; }
	.resume .kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.02em; text-transform: none; }
	.resume .ref { grid-column: 1; display: flex; align-items: baseline; gap: 0.6rem; font-size: 1.15rem; font-weight: 600; }
	.resume .ref [lang='ta'] { font-family: var(--tamil); }
	.resume .ver { font-size: 0.8rem; font-weight: 600; color: var(--muted); letter-spacing: 0.03em; }
	.resume .go { grid-column: 2; grid-row: 1 / span 2; font-size: 1.3rem; color: var(--accent); }
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
	.top { margin: 2.2rem 0 0; max-width: 44rem; }
	.top h2 [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.02em; text-transform: none; }
	.top ol { list-style: none; padding: 0; margin: 0.7rem 0 0; display: grid; gap: 0.5rem; }
	.top a { display: grid; grid-template-columns: 1fr auto; gap: 0.15rem 0.8rem; padding: 0.7rem 1rem; border: var(--bw) solid var(--line); border-radius: 14px; background: var(--surface); color: inherit; text-decoration: none; }
	.top a:hover { border-color: var(--accent); }
	.top .ref { font-weight: 600; }
	.top .ref[lang='ta'], .top .text[lang='ta'] { font-family: var(--tamil); }
	.top .users { font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
	.top .text { grid-column: 1 / -1; color: var(--ink-2); font-size: 0.92rem; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
	@media (max-width: 480px) {
		.books { grid-template-columns: 1fr 1fr; gap: 0.6rem; }
		.book { padding: 0.75rem 0.9rem; }
	}
</style>

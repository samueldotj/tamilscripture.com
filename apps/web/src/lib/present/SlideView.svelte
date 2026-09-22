<script lang="ts">
	// One slide, drawn the same way in the editor's preview and on the
	// presenter's screen (design 11A): a one-line header across the top,
	// verses on the left, notes in a column on the right. A slide without
	// verses is a title page: its header large and its notes centred under it.
	// Every size is a fraction of the slide's longer side (cqmax), so the 16:9
	// preview and a full screen are the same picture at two scales; a passage
	// too long for the frame is shrunk until it fits. References and verse
	// numbers link to the reader.
	import { chapterCached, verseList } from '$lib/content/verses';
	import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
	import Markdown from '$lib/md/Markdown.svelte';
	import { verseKey, verseLabel, verseVersion, type Slide, type SlideVerse } from './types';

	let {
		slide,
		version,
		showNotes = true,
		mode = 'preview',
		lang = 'ta'
	}: {
		slide: Slide;
		/** The presentation's default version code. */
		version: string;
		showNotes?: boolean;
		mode?: 'preview' | 'present';
		/** Interface language, for the notes' lang attribute and placeholders. */
		lang?: 'ta' | 'en';
	} = $props();

	type Loaded = { label: string; verses: { n: string; text: string }[]; lang: 'ta' | 'en'; short: string; code: string; failed?: boolean; ready?: boolean };
	let loaded = $state<Record<string, Loaded>>({});
	const items = $derived(slide.verses.map((v) => ({ v, code: verseVersion(v, version), key: `${verseKey(v)}@${verseVersion(v, version)}` })));
	const title = $derived(slide.title?.trim() ?? '');
	const hasNotes = $derived(slide.notes.trim().length > 0);
	const titlePage = $derived(items.length === 0);
	const notesAside = $derived(showNotes && hasNotes && !titlePage);
	/** Show a version under each verse when they differ, else once for the slide. */
	const mixed = $derived(new Set(items.map((i) => i.code)).size > 1);
	const single = $derived(items.length ? findVersion(items[0].code) : findVersion(version));
	const isTa = (s: string) => /[஀-௿]/.test(s);

	$effect(() => {
		for (const { v, code, key } of items) {
			if (key in loaded) continue;
			const meta = findVersion(code)!;
			const label = verseLabel(v, meta.lang);
			loaded[key] = { label, verses: [], lang: meta.lang, short: meta.short, code };
			chapterCached(fetch, code, v.book, v.chapter)
				.then((ch) => { loaded[key] = { label, verses: verseList(ch, v.start, v.end), lang: meta.lang, short: meta.short, code, ready: true }; })
				.catch(() => { loaded[key] = { label, verses: [], lang: meta.lang, short: meta.short, code, failed: true }; });
		}
	});

	/** Reader link for a verse or range, in the version the slide shows it in. */
	function href(v: SlideVerse, code: string, n?: string): string {
		const book = findBook(v.book);
		if (!book) return '/';
		return chapterUrl(code.toLowerCase(), book, v.chapter, n ?? (v.end > v.start ? `${v.start}-${v.end}` : `${v.start}`));
	}

	/** Shrink the column's type until nothing overflows it (long passages, long notes). */
	function fit(node: HTMLElement) {
		let raf = 0;
		const run = () => {
			cancelAnimationFrame(raf);
			raf = requestAnimationFrame(() => {
				node.style.setProperty('--fit', '1');
				let f = 1;
				while (node.scrollHeight > node.clientHeight + 1 && f > 0.4) {
					f -= 0.05;
					node.style.setProperty('--fit', f.toFixed(2));
				}
			});
		};
		const ro = new ResizeObserver(run);
		ro.observe(node);
		const mo = new MutationObserver(run);
		mo.observe(node, { childList: true, characterData: true, subtree: true });
		document.fonts?.ready.then(run);
		run();
		return { destroy() { ro.disconnect(); mo.disconnect(); cancelAnimationFrame(raf); } };
	}
</script>

<div class="slide {mode}">
	{#if title && !titlePage}
		<header class="head" lang={isTa(title) ? 'ta' : 'en'}>{title}</header>
	{/if}
	<div class="frame" class:aside={notesAside}>
		<div class="main" class:centered={titlePage} use:fit>
			{#if titlePage}
				{#if title}<h2 class="big" lang={isTa(title) ? 'ta' : 'en'}>{title}</h2>{/if}
				{#if hasNotes}
					<div class="notes-main" class:alone={!title}><Markdown source={slide.notes} {version} {lang} /></div>
				{:else if !title}
					<p class="empty" lang={lang}>{lang === 'ta' ? 'வெற்று ஸ்லைடு · வசனம் சேர்க்கவும், அல்லது தலைப்புப் பக்கத்திற்குக் குறிப்புகள் எழுதவும்' : 'Empty slide · add a verse, or write notes for a title page'}</p>
				{/if}
			{/if}
			{#each items as { v, code, key } (key)}
				{@const t = loaded[key]}
				<div class="verse">
					<a class="ref" lang={t?.lang ?? 'ta'} href={href(v, code)} target="_blank" rel="noopener" title={lang === 'ta' ? 'வாசிப்பில் திற' : 'Open in the reader'}>{t?.label ?? verseLabel(v, lang)}</a>
					{#if t?.verses.length}
						<p class="text" lang={t.lang}>
							{#if t.verses.length > 1}
								{#each t.verses as x (x.n)}<a class="vn" href={href(v, code, x.n.split('-')[0])} target="_blank" rel="noopener">{x.n}</a>{x.text}{' '}{/each}
							{:else}
								{t.verses[0].text}
							{/if}
						</p>
					{:else if t?.failed}
						<p class="text muted" lang={lang}>{lang === 'ta' ? 'வசனத்தை ஏற்ற முடியவில்லை' : 'The verse could not be loaded'}</p>
					{:else if t?.ready}
						<p class="text muted">—</p>
					{:else}
						<p class="text muted" aria-busy="true">…</p>
					{/if}
					{#if mixed && t}<span class="ver">{t.short} · {t.lang === 'ta' ? 'தமிழ்' : 'English'}</span>{/if}
				</div>
			{/each}
			{#if items.length && !mixed && single}
				<span class="ver">{single.short} · {single.lang === 'ta' ? 'தமிழ்' : 'English'}</span>
			{/if}
		</div>
		{#if notesAside}
			<aside class="notes" use:fit>
				<Markdown source={slide.notes} {version} {lang} />
			</aside>
		{/if}
	</div>
</div>

<style>
	.slide {
		container-type: size;
		position: relative;
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		overflow: hidden;
		background: #0E1015;
		/* The slide is always night slate (design 11A), whatever the site theme:
		   these override the page tokens for everything drawn inside it. */
		--ink: #F1ECE1;
		--ink-2: #C4BEB1;
		--muted: #B0AA9D;
		--faint: #7E8798;
		--line: #2E323B;
		--accent: #D9B25C;
		--accent-hover: #E5C578;
		--md-heading: var(--ink);
		--md-strong: var(--ink);
		--md-rule: var(--accent);
		--md-quote: var(--muted);
		--md-link: var(--accent);
		--md-code-bg: rgba(255, 255, 255, 0.08);
		color: var(--ink);
	}
	/* One line across the top, whatever the slide holds. */
	.head { flex: none; padding: 2.4cqmax 6.1cqmax 0; font-size: 2cqmax; font-weight: 600; line-height: 1.3; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.head[lang='ta'] { font-family: var(--tamil); }
	/* The flex layout lives one level down: a container query cannot style the
	   container itself, only what is inside it. */
	.frame { display: flex; flex: 1; min-height: 0; width: 100%; }
	.main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; justify-content: center; gap: calc(1.5cqmax * var(--fit, 1)); padding: 3.9cqmax 6.1cqmax; overflow: hidden; }
	.present .main { padding-bottom: 7.6cqmax; }
	.main.centered { align-items: center; text-align: center; }
	.verse { display: flex; flex-direction: column; gap: calc(0.7cqmax * var(--fit, 1)); }
	.ref { align-self: flex-start; font-size: calc(1.53cqmax * var(--fit, 1)); letter-spacing: 0.18em; color: var(--accent); font-weight: 700; font-family: var(--sans); text-decoration: none; border-bottom: 1px solid transparent; }
	.ref:hover, .ref:focus-visible { color: var(--accent-hover); border-bottom-color: var(--accent-hover); }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.text { margin: 0; font-size: calc(2.78cqmax * var(--fit, 1)); line-height: 1.55; text-wrap: pretty; overflow-wrap: anywhere; }
	.text[lang='ta'] { font-family: var(--tamil); }
	.text[lang='en'] { font-family: var(--en); line-height: 1.5; }
	/* Verse numbers inside a range: small, gold, and a link to that verse. */
	.vn { font-family: var(--sans); font-size: 0.55em; font-weight: 700; color: var(--accent); vertical-align: super; line-height: 1; margin-right: 0.3em; text-decoration: none; padding: 0 0.15em; border-radius: 3px; }
	.vn:hover, .vn:focus-visible { background: rgba(217, 178, 92, 0.18); }
	.muted { color: var(--faint); }
	.ver { font-size: calc(1.1cqmax * var(--fit, 1)); letter-spacing: 0.12em; color: var(--faint); font-weight: 600; font-family: var(--sans); }
	.big { margin: 0; font-size: calc(4.4cqmax * var(--fit, 1)); font-weight: 600; line-height: 1.25; color: var(--ink); text-wrap: balance; }
	.big[lang='ta'] { font-family: var(--tamil); }
	/* A title page's notes: centred Markdown, larger when it is all there is. */
	.notes-main { font-size: calc(2.1cqmax * var(--fit, 1)); text-align: center; color: var(--ink-2); width: 100%; max-width: 80cqmax; font-family: var(--tamil); }
	.notes-main.alone { font-size: calc(2.6cqmax * var(--fit, 1)); color: var(--ink); }
	.notes-main :global(ul), .notes-main :global(ol), .notes-main :global(blockquote) { display: inline-block; text-align: left; }
	.empty { color: var(--faint); font-size: 1.6cqmax; font-family: var(--tamil); max-width: 70cqmax; text-wrap: balance; }
	.notes { width: 30.5cqmax; flex: none; border-left: 1.5px solid var(--line); padding: 3.9cqmax 3.9cqmax; display: flex; flex-direction: column; justify-content: center; font-size: calc(1.75cqmax * var(--fit, 1)); line-height: 1.6; color: var(--ink-2); overflow: hidden; font-family: var(--tamil); }
	.present .notes { padding-bottom: 7.6cqmax; }
	/* Portrait screens (a phone held upright): notes drop below the verses. */
	@container (max-aspect-ratio: 1) {
		.frame.aside { flex-direction: column; }
		.frame.aside .notes { width: 100%; flex: none; border-left: 0; border-top: 1.5px solid var(--line); justify-content: flex-start; max-height: 40%; }
	}
</style>

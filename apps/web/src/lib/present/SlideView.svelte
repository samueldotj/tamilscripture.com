<script lang="ts">
	// One slide, drawn the same way in the editor's preview and on the
	// presenter's screen (design 11A): verses on the left, notes in a column
	// on the right. Every size is a fraction of the slide's longer side (cqmax), so
	// the 16:9 preview and a full screen are the same picture at two scales;
	// a passage too long for the frame is shrunk until it fits.
	import { chapterCached, versesText } from '$lib/content/verses';
	import { findVersion } from '$lib/content/manifest';
	import Markdown from '$lib/md/Markdown.svelte';
	import { verseKey, verseLabel, verseVersion, type Slide } from './types';

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

	type Loaded = { label: string; text: string; lang: 'ta' | 'en'; short: string; code: string; failed?: boolean };
	let loaded = $state<Record<string, Loaded>>({});
	const items = $derived(slide.verses.map((v) => ({ v, code: verseVersion(v, version), key: `${verseKey(v)}@${verseVersion(v, version)}` })));
	const title = $derived(slide.title?.trim() ?? '');
	const hasNotes = $derived(slide.notes.trim().length > 0);
	const notesAside = $derived(showNotes && hasNotes && (items.length > 0 || title.length > 0));
	const notesOnly = $derived(!items.length && !title && hasNotes);
	/** Show a version under each verse when they differ, else once for the slide. */
	const mixed = $derived(new Set(items.map((i) => i.code)).size > 1);
	const single = $derived(items.length ? findVersion(items[0].code) : findVersion(version));

	$effect(() => {
		for (const { v, code, key } of items) {
			if (key in loaded) continue;
			const meta = findVersion(code)!;
			const label = verseLabel(v, meta.lang);
			loaded[key] = { label, text: '', lang: meta.lang, short: meta.short, code };
			chapterCached(fetch, code, v.book, v.chapter)
				.then((ch) => { loaded[key] = { label, text: versesText(ch, v.start, v.end) || '—', lang: meta.lang, short: meta.short, code }; })
				.catch(() => { loaded[key] = { label, text: '', lang: meta.lang, short: meta.short, code, failed: true }; });
		}
	});

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
<div class="frame" class:aside={notesAside}>
	<div class="main" class:centered={!items.length} use:fit>
		{#if title}
			<h2 class="title" class:big={!items.length} lang={/[஀-௿]/.test(title) ? 'ta' : 'en'}>{title}</h2>
		{/if}
		{#each items as { v, key } (key)}
			{@const t = loaded[key]}
			<div class="verse">
				<span class="ref" lang={t?.lang ?? 'ta'}>{t?.label ?? verseLabel(v, lang)}</span>
				{#if t?.text}
					<p class="text" lang={t.lang}>{t.text}</p>
				{:else if t?.failed}
					<p class="text muted" lang={lang}>{lang === 'ta' ? 'வசனத்தை ஏற்ற முடியவில்லை' : 'The verse could not be loaded'}</p>
				{:else}
					<p class="text muted" aria-busy="true">…</p>
				{/if}
				{#if mixed && t}<span class="ver">{t.short} · {t.lang === 'ta' ? 'தமிழ்' : 'English'}</span>{/if}
			</div>
		{/each}
		{#if items.length && !mixed && single}
			<span class="ver">{single.short} · {single.lang === 'ta' ? 'தமிழ்' : 'English'}</span>
		{/if}
		{#if notesOnly}
			<!-- The notes are the slide here, so N (hide notes) leaves them in place. -->
			<div class="notes-main"><Markdown source={slide.notes} {version} {lang} /></div>
		{/if}
		{#if !items.length && !title && !hasNotes}
			<p class="empty" lang={lang}>{lang === 'ta' ? 'வெற்று ஸ்லைடு · வசனம் சேர்க்கவும்' : 'Empty slide · add a verse'}</p>
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
	/* The flex layout lives one level down: a container query cannot style the
	   container itself, only what is inside it. */
	.frame { display: flex; width: 100%; height: 100%; }
	.main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; justify-content: center; gap: calc(1.5cqmax * var(--fit, 1)); padding: 3.9cqmax 6.1cqmax; overflow: hidden; }
	.present .main { padding-bottom: 7.6cqmax; }
	.main.centered { align-items: center; text-align: center; }
	.verse { display: flex; flex-direction: column; gap: calc(0.7cqmax * var(--fit, 1)); }
	.ref { font-size: calc(1.53cqmax * var(--fit, 1)); letter-spacing: 0.18em; color: var(--accent); font-weight: 700; font-family: var(--sans); }
	.ref[lang='ta'] { font-family: var(--tamil); }
	.text { margin: 0; font-size: calc(2.78cqmax * var(--fit, 1)); line-height: 1.55; text-wrap: pretty; overflow-wrap: anywhere; }
	.text[lang='ta'] { font-family: var(--tamil); }
	.text[lang='en'] { font-family: var(--en); line-height: 1.5; }
	.muted { color: var(--faint); }
	.ver { font-size: calc(1.1cqmax * var(--fit, 1)); letter-spacing: 0.12em; color: var(--faint); font-weight: 600; font-family: var(--sans); }
	.title { margin: 0; font-size: calc(2cqmax * var(--fit, 1)); font-weight: 600; line-height: 1.3; color: var(--ink); text-wrap: balance; }
	.title.big { font-size: calc(4.4cqmax * var(--fit, 1)); }
	.title[lang='ta'] { font-family: var(--tamil); }
	.notes-main { font-size: calc(2.1cqmax * var(--fit, 1)); text-align: left; color: var(--ink-2); width: 100%; }
	.empty { color: var(--faint); font-size: 1.6cqmax; font-family: var(--tamil); }
	.notes { width: 30.5cqmax; flex: none; border-left: 1.5px solid var(--line); padding: 3.9cqmax 3.9cqmax; display: flex; flex-direction: column; justify-content: center; font-size: calc(1.75cqmax * var(--fit, 1)); line-height: 1.6; color: var(--ink-2); overflow: hidden; font-family: var(--tamil); }
	.present .notes { padding-bottom: 7.6cqmax; }
	/* Portrait screens (a phone held upright): notes drop below the verses. */
	@container (max-aspect-ratio: 1) {
		.frame.aside { flex-direction: column; }
		.frame.aside .notes { width: 100%; flex: none; border-left: 0; border-top: 1.5px solid var(--line); justify-content: flex-start; max-height: 40%; }
	}
</style>

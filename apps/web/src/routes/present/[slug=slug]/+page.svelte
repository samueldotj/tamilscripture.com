<script lang="ts">
	// The presenter (design 11A): one slide at a time on a night-slate screen,
	// opened in its own tab from the editor or from a shared link. Space, →
	// and ↓ advance, ← and ↑ go back, F is fullscreen, N hides the notes, ?
	// shows the keys, Esc leaves fullscreen. The controls fade after 3 s.
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { DEFAULT_VERSION, findVersion, manifest } from '$lib/content/manifest';
	import { chapterCached } from '$lib/content/verses';
	import { myPresentation, presentChannel, type PresentMessage } from '$lib/present/repo';
	import { verseVersion, type Presentation } from '$lib/present/types';
	import SlideView from '$lib/present/SlideView.svelte';
	import ClosingSlide from '$lib/present/ClosingSlide.svelte';

	let { data } = $props();
	const slug = $derived(page.params.slug!);
	const lang = $derived(settings.value.uiLang);
	const ta = $derived(lang === 'ta');

	// The server's copy seeds the state; later changes arrive over the channel or from the owner's session.
	// svelte-ignore state_referenced_locally
	let doc = $state<Presentation | null>(data.presentation);
	let denied = $state(false);
	let index = $state(0);
	let notes = $state(true);
	let controls = $state(true);
	let hint = $state(true);
	let help = $state(false);
	let fullscreen = $state(false);
	let override = $state<string | null>(null);
	let channel: BroadcastChannel | null = null;
	let hideTimer: ReturnType<typeof setTimeout> | undefined;

	// The stored slides plus the closing slide (thanks, votes, share) after them.
	const total = $derived(doc ? doc.slides.length + 1 : 0);
	const closing = $derived(!!doc && index >= doc.slides.length);
	const slide = $derived(doc && !closing ? doc.slides[index] : null);
	const shareUrl = $derived(`https://www.tamilscripture.com/present/${slug}`);
	const version = $derived(findVersion(override ?? '')?.code ?? findVersion(doc?.version ?? '')?.code ?? DEFAULT_VERSION);
	const title = $derived(doc?.title?.trim() || (ta ? 'விளக்கக்காட்சி' : 'Presentation'));
	const description = $derived(
		doc ? `${doc.subtitle ? `${doc.subtitle} · ` : ''}${total} ${ta ? 'ஸ்லைடுகள்' : 'slides'} · Tamil Scripture` : 'Tamil Scripture'
	);

	// A private presentation (or one not shared yet): the owner's own session opens it.
	$effect(() => {
		if (doc || !browser || !session.ready) return;
		if (!session.signedIn) { denied = true; return; }
		myPresentation(slug).then((p) => (p ? (doc = p) : (denied = true))).catch(() => (denied = true));
	});

	// Prefetch the chapters of the next two slides so a step never waits.
	$effect(() => {
		if (!doc) return;
		for (const s of doc.slides.slice(index + 1, index + 3)) {
			for (const v of s.verses) chapterCached(fetch, verseVersion(v, version), v.book, v.chapter).catch(() => {});
		}
	});

	onMount(() => {
		const v = page.url.searchParams.get('v');
		if (v && findVersion(v)) override = findVersion(v)!.code;
		const h = Number(location.hash.slice(1));
		if (h >= 1) index = Math.min(h - 1, total - 1);
		channel = presentChannel(slug);
		if (channel) channel.onmessage = (e: MessageEvent<PresentMessage>) => {
			if (e.data.type === 'doc' && e.data.presentation.slug === slug) doc = e.data.presentation;
		};
		const onFs = () => (fullscreen = !!document.fullscreenElement);
		document.addEventListener('fullscreenchange', onFs);
		wake();
		return () => { document.removeEventListener('fullscreenchange', onFs); clearTimeout(hideTimer); channel?.close(); };
	});

	function go(i: number) {
		if (!doc || !total) return;
		const next = Math.max(0, Math.min(total - 1, i));
		if (next === index) return;
		index = next;
		replaceState(`${location.pathname}${location.search}${next ? `#${next + 1}` : ''}`, page.state);
		channel?.postMessage({ type: 'slide', index: next } satisfies PresentMessage);
	}
	const next = () => go(index + 1);
	const prev = () => go(index - 1);

	function wake() {
		controls = true;
		clearTimeout(hideTimer);
		hideTimer = setTimeout(() => { controls = false; hint = false; }, 3000);
	}
	async function toggleFullscreen() {
		try {
			if (document.fullscreenElement) await document.exitFullscreen();
			else await document.documentElement.requestFullscreen();
		} catch { /* not allowed here */ }
	}
	function setVersion(code: string) {
		override = code === doc?.version ? null : code;
		const url = new URL(location.href);
		if (override) url.searchParams.set('v', override.toLowerCase());
		else url.searchParams.delete('v');
		replaceState(url, page.state);
	}

	function onKey(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA')) return;
		if (e.ctrlKey || e.metaKey || e.altKey) return;
		wake();
		switch (e.key) {
			case ' ': case 'ArrowRight': case 'ArrowDown': case 'PageDown': case 'Enter':
				e.preventDefault(); e.shiftKey && e.key === ' ' ? prev() : next(); break;
			case 'Backspace': case 'ArrowLeft': case 'ArrowUp': case 'PageUp':
				e.preventDefault(); prev(); break;
			case 'Home': e.preventDefault(); go(0); break;
			case 'End': e.preventDefault(); go(total - 1); break;
			case 'f': case 'F': toggleFullscreen(); break;
			case 'n': case 'N': notes = !notes; break;
			case '?': help = !help; break;
			case 'Escape': if (help) help = false; break;
		}
	}
	// Taps on the slide: the right two thirds advance, the left third goes back.
	let touchX = 0, touchY = 0;
	function onTap(e: MouseEvent) {
		const el = e.target as HTMLElement | null;
		if (el?.closest('a, button, select, [role="dialog"]')) return;
		wake();
		e.clientX < innerWidth / 3 ? prev() : next();
	}
	function onTouchStart(e: TouchEvent) { touchX = e.touches[0].clientX; touchY = e.touches[0].clientY; }
	function onTouchEnd(e: TouchEvent) {
		const dx = e.changedTouches[0].clientX - touchX, dy = e.changedTouches[0].clientY - touchY;
		if (Math.abs(dx) > 60 && Math.abs(dy) < 50) { e.preventDefault(); dx < 0 ? next() : prev(); }
	}
</script>

<svelte:head>
	<title>{title} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<meta name="robots" content="noindex" />
	<meta name="theme-color" content="#0E1015" />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="article" />
	<meta property="og:url" content={`https://www.tamilscripture.com/present/${slug}`} />
</svelte:head>

<svelte:window onkeydown={onKey} onmousemove={wake} onpointerdown={wake} />

<div class="presenter" class:idle={!controls}>
	{#if doc && (slide || closing)}
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -- keys are handled on the window; a tap is the touch shortcut -->
		<div class="stage" onclick={onTap} ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
			{#if slide}
				{#key slide.id + version}
					<SlideView {slide} {version} showNotes={notes} mode="present" {lang} />
				{/key}
			{:else}
				<ClosingSlide {slug} title={doc.title} subtitle={doc.subtitle} votes={{ up: doc.votes_up ?? 0, down: doc.votes_down ?? 0 }} shared={doc.visibility === 'link'} {shareUrl} {lang} />
			{/if}
		</div>

		<!-- progress hairline -->
		<div class="progress" aria-hidden="true"><div style="width: {((index + 1) / total) * 100}%"></div></div>

		<!-- controls, auto-hide -->
		<div class="controls">
			<div class="pill">
				<button type="button" class="ic" onclick={prev} disabled={index === 0} aria-label={ta ? 'முந்தைய ஸ்லைடு' : 'Previous slide'}>‹</button>
				<span class="count"><span>{index + 1}</span><span class="of">/ {total}</span></span>
				<button type="button" class="ic" onclick={next} disabled={index >= total - 1} aria-label={ta ? 'அடுத்த ஸ்லைடு' : 'Next slide'}>›</button>
				<span class="sep"></span>
				<button type="button" class="txt" onclick={toggleFullscreen} aria-pressed={fullscreen}><span class="glyph" aria-hidden="true">⛶</span>{fullscreen ? (ta ? 'வெளியேறு' : 'Exit') : 'Fullscreen'}<kbd>F</kbd></button>
				<button type="button" class="txt" class:on={notes} onclick={() => (notes = !notes)} aria-pressed={notes} lang="ta">குறிப்புகள்<kbd>N</kbd></button>
				<select class="ver" value={version} onchange={(e) => setVersion(e.currentTarget.value)} aria-label={ta ? 'மொழிபெயர்ப்பு' : 'Version'}>
					{#each manifest.versions as v (v.code)}<option value={v.code}>{v.short}</option>{/each}
				</select>
				<button type="button" class="ic q" onclick={() => (help = !help)} aria-label={ta ? 'விசைகள்' : 'Keyboard shortcuts'} aria-expanded={help}>?</button>
			</div>
		</div>

		<!-- shortcut hint toast (shown on open, fades with the controls) -->
		{#if hint || help}
			<div class="hint" class:help role={help ? 'dialog' : undefined} aria-label={help ? (ta ? 'விசைகள்' : 'Keyboard shortcuts') : undefined}>
				<span><kbd>Space</kbd> <kbd>→</kbd> <kbd>↓</kbd> {ta ? 'அடுத்து' : 'next'}</span>
				<span><kbd>←</kbd> <kbd>↑</kbd> {ta ? 'பின்' : 'back'}</span>
				{#if help}
					<span><kbd>Home</kbd> <kbd>End</kbd> {ta ? 'முதல் · கடைசி' : 'first · last'}</span>
					<span><kbd>F</kbd> fullscreen</span>
					<span><kbd>N</kbd> {ta ? 'குறிப்புகள்' : 'notes'}</span>
				{/if}
				<span><kbd>Esc</kbd> {ta ? 'வெளியேறு' : 'exit'}</span>
			</div>
		{/if}
		<div class="who" aria-hidden="true">{doc.title}{doc.subtitle ? ` · ${doc.subtitle}` : ''}</div>
	{:else if denied}
		<div class="message">
			<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த விளக்கக்காட்சி தனிப்பட்டது' : 'This presentation is private'}</h1>
			<p lang={ta ? 'ta' : 'en'}>{ta ? 'இணைப்பு தவறாக இருக்கலாம், அல்லது உரிமையாளர் இதைப் பகிரவில்லை.' : 'The link may be wrong, or its owner has not shared it.'}</p>
			{#if !session.signedIn}<p><a href={`/signin?next=${encodeURIComponent(page.url.pathname)}`} lang={ta ? 'ta' : 'en'}>{ta ? 'உங்களுடையதா? உள்நுழையவும்' : 'Yours? Sign in'}</a></p>{/if}
			<p><a href="/" lang="ta">‹ தமிழ் வேதாகமம்</a></p>
		</div>
	{:else}
		<div class="message" aria-busy="true"><p>…</p></div>
	{/if}
</div>

<style>
	.presenter { position: fixed; inset: 0; background: #0E1015; color: #F1ECE1; overflow: hidden; --pill-bg: rgba(32, 35, 42, 0.92); --pill-line: #3A3F4A; --faint: #7E8798; }
	.presenter.idle { cursor: none; }
	.stage { position: absolute; inset: 0; }
	.progress { position: absolute; left: 0; right: 0; top: 0; height: 3px; background: #2E323B; }
	.progress div { height: 3px; background: #D9B25C; transition: width 0.25s ease; }
	.controls { position: absolute; left: 0; right: 0; bottom: 24px; display: flex; justify-content: center; transition: opacity 0.3s ease; }
	.idle .controls, .idle .hint:not(.help), .idle .who { opacity: 0; pointer-events: none; }
	.pill { display: flex; align-items: center; gap: 6px; padding: 8px; border-radius: 16px; background: var(--pill-bg); border: 1.5px solid var(--pill-line); backdrop-filter: blur(10px); max-width: calc(100vw - 32px); flex-wrap: wrap; justify-content: center; }
	.ic { width: 44px; height: 44px; border-radius: 12px; border: 0; background: none; color: #F1ECE1; font-size: 1.3rem; cursor: pointer; }
	.ic:disabled { opacity: 0.35; cursor: default; }
	.ic:not(:disabled):hover, .txt:hover { background: #3A3F4A; }
	.q { font-size: 1rem; font-weight: 800; color: #C4BEB1; }
	.count { display: flex; align-items: baseline; gap: 4px; padding: 0 10px; font-size: 1rem; font-weight: 700; }
	.of { color: var(--faint); font-weight: 600; }
	.sep { width: 1px; height: 24px; background: var(--pill-line); margin: 0 4px; }
	.txt { height: 44px; padding: 0 14px; border-radius: 12px; border: 0; background: none; color: #F1ECE1; font-size: 0.88rem; font-weight: 700; display: flex; align-items: center; gap: 8px; cursor: pointer; }
	.txt[lang='ta'] { font-family: var(--tamil); }
	.txt.on { background: #3A3F4A; }
	.glyph { font-size: 1rem; }
	kbd { font: 700 0.68rem var(--sans); color: #B0AA9D; border: 1px solid #5A6070; border-radius: 4px; padding: 1px 5px; }
	.ver { height: 36px; border-radius: 10px; border: 1px solid var(--pill-line); background: #262930; color: #F1ECE1; font: 700 0.8rem var(--sans); padding: 0 8px; }
	.hint { position: absolute; left: 24px; bottom: 24px; display: flex; align-items: center; gap: 14px; padding: 10px 14px; border-radius: 12px; background: var(--pill-bg); border: 1.5px solid var(--pill-line); backdrop-filter: blur(10px); font-size: 0.82rem; color: #C4BEB1; white-space: nowrap; transition: opacity 0.3s ease; font-family: var(--tamil); }
	.hint kbd { color: #F1ECE1; }
	.hint.help { flex-direction: column; align-items: flex-start; gap: 8px; bottom: 96px; }
	.who { position: absolute; right: 24px; bottom: 32px; font-size: 0.82rem; color: var(--faint); white-space: nowrap; max-width: 40vw; overflow: hidden; text-overflow: ellipsis; font-family: var(--tamil); transition: opacity 0.3s ease; }
	.message { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 2rem; gap: 0.4rem; }
	.message h1 { font-size: 1.5rem; margin: 0; }
	.message p { margin: 0; color: #C4BEB1; }
	.message [lang='ta'] { font-family: var(--tamil); }
	.message a { color: #D9B25C; }
	@media (max-width: 720px) {
		.hint, .who { display: none; }
		.controls { bottom: 12px; }
		.txt { padding: 0 10px; font-size: 0.8rem; }
		.txt kbd { display: none; }
	}
	@media (prefers-reduced-motion: reduce) {
		.controls, .hint, .who, .progress div { transition: none; }
	}
</style>

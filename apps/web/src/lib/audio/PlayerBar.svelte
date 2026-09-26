<script lang="ts">
	// The slim player bar (design 12B desktop, 12A phone): under the reading
	// column on chapter pages, across the foot of the window elsewhere. A chunk
	// of its own, loaded the first time something plays.
	import { chapterUrl } from '$lib/content/manifest';
	import { player } from './player.svelte';

	let { lang, column = false }: { lang: 'ta' | 'en'; /** dock under the reader's middle column */ column?: boolean } = $props();

	const ta = $derived(lang === 'ta');
	const t = $derived(player.track);
	const name = $derived(t ? (t.version.lang === 'ta' ? t.book.name_ta : t.book.name_en) : '');
	const label = $derived(t ? `${name} ${t.chapter}${player.verse !== null ? `:${player.verse}` : ''}` : '');
	const href = $derived(t ? chapterUrl(player.viewing?.versionPath ?? t.version.code.toLowerCase(), t.book, t.chapter) : '#');
	const away = $derived(!!t && player.viewing?.key !== player.key);
	const total = $derived(player.duration || (t ? t.ms / 1000 : 0));

	function clock(s: number) {
		if (!isFinite(s) || s < 0) s = 0;
		const m = Math.floor(s / 60), sec = Math.floor(s % 60);
		return `${m}:${String(sec).padStart(2, '0')}`;
	}
	const position = $derived(
		player.error === 'unavailable' ? (ta ? 'ஒலி கிடைக்கவில்லை' : 'Audio unavailable')
		: player.error === 'gap' ? (ta ? 'அடுத்த அதிகாரத்துக்கு ஒலி இல்லை' : 'No audio for the next chapter')
		: t?.verses?.length && player.verseIndex ? `${player.verseIndex} / ${t.verses.length}`
		: `${clock(player.time)} / ${clock(total)}`
	);
	const rateLabel = $derived(`${player.rate}×`);


	function onKey(e: KeyboardEvent) {
		const el = e.target as HTMLElement | null;
		if (!t || e.ctrlKey || e.metaKey || e.altKey) return;
		if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable)) return;
		const k = e.key.toLowerCase();
		if (k === 'k') player.toggle();
		else if (k === 'j') player.skip(-10);
		else if (k === 'l') player.skip(10);
		else return;
		e.preventDefault();
	}
</script>

<svelte:window onkeydown={onKey} />

{#if t}
	<section class="player" class:column aria-label={ta ? 'ஒலி வேதாகமம்' : 'Audio Bible'} lang={lang}>
		<div class="row">
			<button type="button" class="ic wide-only" onclick={() => player.prevChapter()} disabled={!t.prev} aria-label={ta ? 'முந்தைய அதிகாரம்' : 'Previous chapter'} title={ta ? 'முந்தைய அதிகாரம்' : 'Previous chapter'}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 5h2.2v14H6zM20 5v14L9.5 12z"/></svg>
			</button>
			<button type="button" class="ic" onclick={() => player.skip(-10)} aria-label={ta ? '10 விநாடி பின்' : 'Back 10 seconds'} title={ta ? '10 விநாடி பின் (J)' : 'Back 10 s (J)'}>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><text x="12" y="15.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="currentColor" stroke="none" font-family="system-ui, sans-serif">10</text></svg>
			</button>
			<button type="button" class="pp" onclick={() => player.toggle()} aria-label={player.playing ? (ta ? 'இடைநிறுத்து' : 'Pause') : (ta ? 'கேள்' : 'Play')} title={ta ? 'இயக்கு / நிறுத்து (K)' : 'Play / pause (K)'}>
				{#if player.loading && player.playing}
					<span class="spin" aria-hidden="true"></span>
				{:else if player.playing}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 4h4.5v16H6zM13.5 4H18v16h-4.5z"/></svg>
				{:else}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.5v15L19.5 12z"/></svg>
				{/if}
			</button>
			<button type="button" class="ic" onclick={() => player.skip(10)} aria-label={ta ? '10 விநாடி முன்' : 'Forward 10 seconds'} title={ta ? '10 விநாடி முன் (L)' : 'Forward 10 s (L)'}>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/><text x="12" y="15.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="currentColor" stroke="none" font-family="system-ui, sans-serif">10</text></svg>
			</button>
			<button type="button" class="ic wide-only" onclick={() => player.nextChapter()} disabled={!t.next} aria-label={ta ? 'அடுத்த அதிகாரம்' : 'Next chapter'} title={ta ? 'அடுத்த அதிகாரம்' : 'Next chapter'}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M15.8 5H18v14h-2.2zM4 5v14l10.5-7z"/></svg>
			</button>
			<div class="what">
				{#if away}
					<a class="ref" {href} lang={t.version.lang} title={ta ? 'வாசிக்கப்படும் அதிகாரத்துக்குச் செல்' : 'Go to the chapter being read'}>{label}</a>
				{:else}
					<span class="ref" lang={t.version.lang}>{label}</span>
				{/if}
				<input
					class="seek"
					type="range"
					min="0"
					max={Math.max(1, total)}
					step="0.1"
					value={player.time}
					style="--p: {total ? Math.min(100, (player.time / total) * 100) : 0}%"
					aria-label={ta ? 'நிலை' : 'Position'}
					aria-valuetext={`${clock(player.time)} / ${clock(total)}`}
					oninput={(e) => player.seek(Number((e.currentTarget as HTMLInputElement).value))}
				/>
				<span class="pos" class:err={!!player.error} aria-live="polite">{position}</span>
			</div>
			<button type="button" class="rate" onclick={() => player.cycleRate()} aria-label={ta ? `வேகம் ${rateLabel}` : `Speed ${rateLabel}`} title={ta ? 'வேகம்' : 'Speed'}>{rateLabel}</button>
			<button type="button" class="ic x" onclick={() => player.close()} aria-label={ta ? 'ஒலியை மூடு' : 'Close audio'}>✕</button>
		</div>
	</section>
{/if}

<style>
	/* Design 12B: a slim bar docked under the text, 12px 40px padding, a 40px
	   gold play button, the reference, a 4px progress track, n / N, speed, ✕. */
	/* The bar's height, for what must clear it (the verse action pill, the text size card, the page end). */
	:global(html:has(section.player)) { --player-h: calc(64px + env(safe-area-inset-bottom) + var(--bw)); }
	.player { position: fixed; z-index: 16; left: 0; right: 0; bottom: 0; background: var(--bg); border-top: var(--bw) solid var(--line); padding-bottom: env(safe-area-inset-bottom); }
	.row { display: flex; align-items: center; gap: 14px; padding: 12px 40px; max-width: 74rem; margin: 0 auto; }
	.column .row { max-width: none; }
	.what { flex: 1; min-width: 0; display: flex; align-items: center; gap: 14px; }
	.ref { flex: none; max-width: 40%; }
	.ref { font-family: var(--sans); font-size: 16px; font-weight: 600; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-decoration: none; }
	.ref[lang='ta'] { font-family: var(--tamil); }
	a.ref:hover { color: var(--accent); text-decoration: underline; text-underline-offset: 0.2em; }
	.pos { margin-left: auto; font-family: var(--sans); font-size: 13px; color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
	.pos.err { color: var(--amber); }
	.pp { width: 40px; height: 40px; flex: none; border: 0; border-radius: 999px; background: var(--accent); color: var(--on-accent); display: flex; align-items: center; justify-content: center; cursor: pointer; }
	.pp:hover { background: var(--accent-hover); }
	.ic { width: 32px; height: 32px; flex: none; border: 0; border-radius: 999px; background: none; color: var(--muted); display: flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; font-size: 16px; }
	.ic:hover:not(:disabled) { background: var(--surface-2); color: var(--ink); }
	.ic:disabled { opacity: 0.35; cursor: default; }
	.rate { flex: none; font-family: var(--sans); font-size: 13px; font-weight: 700; color: var(--ink-2); border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 5px 10px; background: none; cursor: pointer; font-variant-numeric: tabular-nums; min-width: 3.1rem; }
	.rate:hover { border-color: var(--accent); }
	.spin { width: 16px; height: 16px; border-radius: 999px; border: 2px solid currentColor; border-right-color: transparent; animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }

	/* The progress track is the seek control: a 4px line between the reference
	   and n / N, as the design draws it, with a 20px hit area. */
	.seek { flex: 1; min-width: 4rem; height: 20px; margin: 0; background: transparent; -webkit-appearance: none; appearance: none; cursor: pointer; }
	.seek::-webkit-slider-runnable-track { height: 4px; background: linear-gradient(to right, var(--accent) var(--p), var(--line-2) var(--p)); border-radius: 999px; }
	.seek::-moz-range-track { height: 4px; background: linear-gradient(to right, var(--accent) var(--p), var(--line-2) var(--p)); border-radius: 999px; }
	.seek::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; margin-top: -4px; border-radius: 999px; background: var(--accent); border: 0; opacity: 0; transition: opacity 0.15s; }
	.seek::-moz-range-thumb { width: 12px; height: 12px; border-radius: 999px; background: var(--accent); border: 0; opacity: 0; }
	.seek:hover::-webkit-slider-thumb, .seek:focus-visible::-webkit-slider-thumb { opacity: 1; }
	.seek:hover::-moz-range-thumb, .seek:focus-visible::-moz-range-thumb { opacity: 1; }
	.seek:focus-visible { outline: none; }

	/* Under the reading column (design 12B): the same offsets as the reader's grid. */
	@media (min-width: 960px) {
		.column { left: clamp(16.75rem, 21vw, 19.5rem); }
	}
	@media (min-width: 1180px) {
		.column { right: clamp(21.5rem, 27vw, 26.25rem); }
	}

	/* Phones (design 12A): the bar takes the thumb bar's place — a 3px line on
	   top, a 52px play button, the reference over n / N, speed and close. */
	@media (max-width: 720px) {
		:global(html:has(section.player)) { --player-h: calc(64px + max(22px, env(safe-area-inset-bottom)) + var(--bw)); }
		.row { gap: 8px; padding: 12px 14px max(22px, env(safe-area-inset-bottom)); }
		.player { padding-bottom: 0; }
		.wide-only { display: none; }
		.pp { width: 52px; height: 52px; }
		.pp svg { width: 18px; height: 18px; }
		.what { flex-direction: column; align-items: flex-start; gap: 0; }
		.ref { font-size: 17px; max-width: 100%; }
		/* The line across the top of the bar (12A). */
		.pos { margin-left: 0; font-size: 12px; }
		.ic { width: 40px; height: 44px; }
		.ic.x { font-size: 20px; }
		.rate { height: 44px; min-width: 44px; padding: 0 10px; font-size: 14px; }
		.seek { position: absolute; left: 0; right: 0; top: -9px; width: 100%; min-width: 0; }
		.seek::-webkit-slider-runnable-track { height: 3px; border-radius: 0; }
		.seek::-moz-range-track { height: 3px; border-radius: 0; }
	}
	@media (prefers-reduced-motion: reduce) {
		.spin { animation-duration: 2.4s; }
	}
</style>

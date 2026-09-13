<script lang="ts">
	// Context overlay for screens without the desktop column: a right-hand
	// drawer on tablets and a bottom sheet on phones (design 04), with tabs
	// for related verses and the chapter's places.
	import { findBook } from '$lib/content/manifest';
	import type { XrefTarget } from '$lib/content/types';
	import type { ChapterMentions } from '$lib/entities/types';
	import XrefList from './XrefList.svelte';
	import PlacesPanel from '$lib/entities/PlacesPanel.svelte';

	let {
		tab = $bindable('related'),
		verseId = null,
		targets = null,
		version,
		versionPath,
		lang,
		chapterLabel = '',
		mentions = null,
		mapSvg = null,
		placesLoading = false,
		selected = new Set<string>(),
		onclose
	}: {
		tab?: 'related' | 'places';
		verseId?: string | null;
		targets?: XrefTarget[] | null;
		version: string;
		versionPath: string;
		lang: 'ta' | 'en';
		chapterLabel?: string;
		mentions?: ChapterMentions | null;
		mapSvg?: string | null;
		placesLoading?: boolean;
		selected?: Set<string>;
		onclose: () => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	const verseLabel = $derived.by(() => {
		if (!verseId) return '';
		const [code, ch, v] = verseId.split('.');
		const book = findBook(code)!;
		return `${ta ? book.name_ta : book.name_en} ${ch}:${v}`;
	});
	const placeCount = $derived(mentions ? Object.keys(mentions.places).length : 0);
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onclose} onkeydown={onKey}></div>
<div class="xref-panel" aria-label={ta ? 'சூழல்' : 'Context'} role="dialog" tabindex="-1" onkeydown={onKey}>
	<span class="grab" aria-hidden="true"></span>
	<div class="top">
		<div class="tabs" role="tablist">
			<button type="button" role="tab" aria-selected={tab === 'related'} class:on={tab === 'related'} onclick={() => (tab = 'related')} lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related'}</button>
			<button type="button" role="tab" aria-selected={tab === 'places'} class:on={tab === 'places'} onclick={() => (tab = 'places')} lang={ta ? 'ta' : 'en'}>{ta ? 'இடங்கள்' : 'Places'}{#if placeCount} <span class="count">{placeCount}</span>{/if}</button>
		</div>
		<button type="button" class="close" onclick={onclose} aria-label={ta ? 'மூடு' : 'Close'}>✕</button>
	</div>
	{#if tab === 'related'}
		<header>
			<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'}</div>
			{#if verseId}
				<h2 lang={ta ? 'ta' : 'en'}>{verseLabel} <span class="n">· {targets?.length ?? 0} {ta ? 'குறிப்புகள்' : 'refs'}</span></h2>
			{:else}
				<h2 class="empty" lang={ta ? 'ta' : 'en'}>{ta ? 'வசனத்தின் ‡ குறியைத் தொடுங்கள்' : 'Tap a verse’s ‡ marker'}</h2>
			{/if}
		</header>
		{#if verseId && targets?.length}
			<XrefList {targets} {version} {lang} onnavigate={onclose} />
		{/if}
	{:else}
		<header>
			<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'இடங்கள்' : 'Places'}</div>
			<h2 lang={ta ? 'ta' : 'en'}>{chapterLabel}</h2>
		</header>
		<PlacesPanel {mentions} {mapSvg} {selected} {lang} {versionPath} loading={placesLoading} />
	{/if}
</div>

<style>
	.backdrop { position: fixed; inset: 0; z-index: 20; background: transparent; }
	.xref-panel { position: fixed; z-index: 21; right: 0; top: 0; bottom: 0; width: min(26rem, 100%); overflow-y: auto; background: var(--surface); border-left: var(--bw) solid var(--line); padding: 1rem 1.4rem 2rem; box-shadow: var(--shadow-lg); }
	.grab { display: none; }
	.top { display: flex; align-items: center; gap: 0.6rem; }
	.tabs { flex: 1; display: flex; gap: 0.3rem; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.tabs button { flex: 1; border: 0; border-radius: 9px; padding: 0.5rem 0.4rem; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.85rem; cursor: pointer; min-height: 38px; }
	.tabs button[lang='ta'] { font-family: var(--tamil); }
	.tabs button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.tabs .count { font-size: 0.72rem; color: var(--muted); margin-left: 0.15rem; }
	header { padding: 1rem 0 0.9rem; margin-bottom: 0.4rem; border-bottom: var(--bw) solid var(--line); }
	h2 { font-size: 1.2rem; margin: 0.15rem 0 0; font-weight: 600; }
	h2[lang='ta'] { font-family: var(--tamil); }
	h2.empty { color: var(--muted); font-weight: 500; font-size: 1.05rem; }
	.n { font-size: 0.8rem; color: var(--muted); font-weight: 400; font-family: var(--sans); }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.close { flex: none; width: 40px; height: 40px; border-radius: 999px; border: 0; background: var(--surface-2); color: var(--ink-2); font-size: 0.95rem; cursor: pointer; }
	.close:hover { color: var(--ink); }
	@media (max-width: 720px) {
		.backdrop { background: var(--scrim); }
		.xref-panel { top: 14%; width: 100%; border-left: 0; border-top: var(--bw) solid var(--line-2); border-radius: 26px 26px 0 0; padding-top: 0.75rem; }
		.grab { display: block; width: 44px; height: 5px; border-radius: 999px; background: var(--line-2); margin: 0 auto 0.8rem; }
	}
</style>

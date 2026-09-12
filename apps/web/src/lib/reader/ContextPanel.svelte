<script lang="ts">
	// Desktop context column (design 3A): tabs for related verses and the
	// places named in the chapter, with the verse actions underneath.
	// Rendered permanently on wide screens so opening it pushes nothing around.
	import type { Snippet } from 'svelte';
	import type { XrefTarget } from '$lib/content/types';
	import type { ChapterMentions } from '$lib/entities/types';
	import XrefList from './XrefList.svelte';
	import PlacesPanel from '$lib/entities/PlacesPanel.svelte';

	let {
		tab = $bindable('places'),
		label = '',
		chapterLabel = '',
		targets = null,
		xrefsEnabled = true,
		version,
		versionPath,
		lang,
		mentions = null,
		mapSvg = null,
		placesLoading = false,
		selected = new Set<string>(),
		actions
	}: {
		tab?: 'related' | 'places';
		/** verse or range label for the header; empty when nothing is selected */
		label?: string;
		/** "Acts 13" for the places header */
		chapterLabel?: string;
		targets?: XrefTarget[] | null;
		xrefsEnabled?: boolean;
		version: string;
		versionPath: string;
		lang: 'ta' | 'en';
		mentions?: ChapterMentions | null;
		mapSvg?: string | null;
		placesLoading?: boolean;
		selected?: Set<string>;
		actions?: Snippet;
	} = $props();

	const ta = $derived(lang === 'ta');
	const placeCount = $derived(mentions ? Object.keys(mentions.places).length : 0);
</script>

<div class="context">
	<div class="tabs" role="tablist" aria-label={ta ? 'சூழல்' : 'Context'}>
		<button type="button" role="tab" aria-selected={tab === 'related'} class:on={tab === 'related'} onclick={() => (tab = 'related')} lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'}</button>
		<button type="button" role="tab" aria-selected={tab === 'places'} class:on={tab === 'places'} onclick={() => (tab = 'places')} lang={ta ? 'ta' : 'en'}>{ta ? 'இடங்கள்' : 'Places'}{#if placeCount} <span class="count">{placeCount}</span>{/if}</button>
	</div>

	{#if tab === 'related'}
		<header>
			<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'}</div>
			{#if label}
				<h2 lang={ta ? 'ta' : 'en'}>{label}{#if targets?.length} <span class="n">· {targets.length} {ta ? 'குறிப்புகள்' : 'refs'}</span>{/if}</h2>
			{:else}
				<h2 class="empty" lang={ta ? 'ta' : 'en'}>{ta ? 'வசனம் தேர்வு செய்யவில்லை' : 'No verse selected'}</h2>
			{/if}
		</header>
		<div class="body">
			{#if !label}
				<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒரு வசன எண்ணைத் தொட்டால் அதன் தொடர்புள்ள வசனங்கள் இங்கே காட்டப்படும். அடிக்கோடிட, குறிப்பு எழுத, நகலெடுக்க, பகிர இங்கேயே செய்யலாம்.' : 'Tap a verse number to see its related verses here, and to highlight, note, copy or share it.'}</p>
			{:else if !xrefsEnabled}
				<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒப்புவசனங்கள் அமைப்புகளில் அணைக்கப்பட்டுள்ளன.' : 'Cross-references are switched off in settings.'}</p>
			{:else if targets?.length}
				<XrefList {targets} {version} {lang} />
			{:else}
				<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த வசனத்திற்கு தொடர்புள்ள வசனங்கள் பட்டியலிடப்படவில்லை.' : 'No related verses are listed for this verse.'}</p>
			{/if}
		</div>
	{:else}
		<header>
			<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'இடங்கள்' : 'Places'}</div>
			<h2 lang={ta ? 'ta' : 'en'}>{chapterLabel}</h2>
		</header>
		<div class="body">
			<PlacesPanel {mentions} {mapSvg} {selected} {lang} {versionPath} loading={placesLoading} />
		</div>
	{/if}

	{#if actions && label}
		<footer>
			{@render actions()}
		</footer>
	{/if}
</div>

<style>
	.context { display: flex; flex-direction: column; min-height: 100%; }
	.tabs { display: flex; gap: 0.3rem; margin: 0.9rem 1.4rem 0; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.tabs button { flex: 1; border: 0; border-radius: 9px; padding: 0.5rem 0.4rem; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.85rem; cursor: pointer; min-height: 38px; }
	.tabs button[lang='ta'] { font-family: var(--tamil); }
	.tabs button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.tabs .count { font-size: 0.72rem; color: var(--muted); font-weight: 600; margin-left: 0.15rem; }
	header { padding: 1rem 1.4rem 0.8rem; border-bottom: var(--bw) solid var(--line); }
	h2 { font-size: 1.2rem; margin: 0.15rem 0 0; font-weight: 600; }
	h2[lang='ta'] { font-family: var(--tamil); }
	h2.empty { color: var(--muted); font-weight: 500; font-size: 1.05rem; }
	.n { font-size: 0.8rem; color: var(--muted); font-weight: 400; font-family: var(--sans); }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.body { flex: 1; padding: 0.6rem 1.4rem 1.4rem; }
	.hint { color: var(--muted); line-height: 1.7; margin: 0.8rem 0 0; font-size: 0.95rem; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	footer { position: sticky; bottom: 0; padding: 1rem 1.4rem; border-top: var(--bw) solid var(--line); background: var(--surface); }
</style>

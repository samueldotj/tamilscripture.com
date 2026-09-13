<script lang="ts">
	// Desktop context column (design 3A): tabs for related verses, places,
	// people and dictionary articles, with the verse actions underneath.
	// Rendered permanently on wide screens so opening it pushes nothing around.
	import type { Snippet } from 'svelte';
	import type { XrefTarget } from '$lib/content/types';
	import type { ChapterMentions } from '$lib/entities/types';
	import XrefList from './XrefList.svelte';
	import PlacesPanel from '$lib/entities/PlacesPanel.svelte';
	import PeoplePanel from '$lib/entities/PeoplePanel.svelte';
	import DictionaryPanel from '$lib/entities/DictionaryPanel.svelte';

	export type PanelTab = 'related' | 'places' | 'people' | 'dictionary';

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
		tab?: PanelTab;
		/** verse or range label for the header; empty when nothing is selected */
		label?: string;
		/** "Acts 13" for the entity headers */
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
	const peopleCount = $derived(mentions?.people ? Object.keys(mentions.people).length : 0);
	const tabs = $derived<{ id: PanelTab; ta: string; en: string; n?: number }[]>([
		{ id: 'related', ta: 'தொடர்பு', en: 'Related' },
		{ id: 'places', ta: 'இடங்கள்', en: 'Places', n: placeCount },
		{ id: 'people', ta: 'நபர்கள்', en: 'People', n: peopleCount },
		{ id: 'dictionary', ta: 'அகராதி', en: 'Dictionary' }
	]);
	const heading = $derived.by(() => {
		switch (tab) {
			case 'related': return ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses';
			case 'places': return ta ? 'இடங்கள்' : 'Places';
			case 'people': return ta ? 'நபர்கள்' : 'People';
			default: return ta ? 'அகராதி' : 'Dictionary';
		}
	});
</script>

<div class="context">
	<div class="tabs" role="tablist" aria-label={ta ? 'சூழல்' : 'Context'}>
		{#each tabs as t (t.id)}
			<button type="button" role="tab" aria-selected={tab === t.id} class:on={tab === t.id} onclick={() => (tab = t.id)} lang={ta ? 'ta' : 'en'}>{ta ? t.ta : t.en}{#if t.n} <span class="count">{t.n}</span>{/if}</button>
		{/each}
	</div>

	<header>
		<div class="kicker" lang={ta ? 'ta' : 'en'}>{heading}</div>
		{#if tab === 'related'}
			{#if label}
				<h2 lang={ta ? 'ta' : 'en'}>{label}{#if targets?.length} <span class="n">· {targets.length} {ta ? 'குறிப்புகள்' : 'refs'}</span>{/if}</h2>
			{:else}
				<h2 class="empty" lang={ta ? 'ta' : 'en'}>{ta ? 'வசனம் தேர்வு செய்யவில்லை' : 'No verse selected'}</h2>
			{/if}
		{:else}
			<h2 lang={ta ? 'ta' : 'en'}>{label || chapterLabel}</h2>
		{/if}
	</header>

	<div class="body">
		{#if tab === 'related'}
			{#if !label}
				<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒரு வசன எண்ணைத் தொட்டால் அதன் தொடர்புள்ள வசனங்கள் இங்கே காட்டப்படும். அடிக்கோடிட, குறிப்பு எழுத, நகலெடுக்க, பகிர இங்கேயே செய்யலாம்.' : 'Tap a verse number to see its related verses here, and to highlight, note, copy or share it.'}</p>
			{:else if !xrefsEnabled}
				<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒப்புவசனங்கள் அமைப்புகளில் அணைக்கப்பட்டுள்ளன.' : 'Cross-references are switched off in settings.'}</p>
			{:else if targets?.length}
				<XrefList {targets} {version} {lang} />
			{:else}
				<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த வசனத்திற்கு தொடர்புள்ள வசனங்கள் பட்டியலிடப்படவில்லை.' : 'No related verses are listed for this verse.'}</p>
			{/if}
		{:else if tab === 'places'}
			<PlacesPanel {mentions} {mapSvg} {selected} {lang} {versionPath} loading={placesLoading} />
		{:else if tab === 'people'}
			<PeoplePanel {mentions} {selected} {lang} {versionPath} loading={placesLoading} />
		{:else}
			<DictionaryPanel {mentions} {selected} {lang} loading={placesLoading} />
		{/if}
	</div>

	{#if actions && label}
		<footer>
			{@render actions()}
		</footer>
	{/if}
</div>

<style>
	.context { display: flex; flex-direction: column; min-height: 100%; }
	.tabs { display: flex; gap: 0.25rem; margin: 0.9rem 1.2rem 0; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.tabs button { flex: 1; border: 0; border-radius: 9px; padding: 0.45rem 0.2rem; background: transparent; color: var(--muted); font-weight: 600; font-size: 0.78rem; cursor: pointer; min-height: 38px; white-space: nowrap; }
	.tabs button[lang='ta'] { font-family: var(--tamil); font-size: 0.82rem; }
	.tabs button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.tabs .count { font-size: 0.7rem; color: var(--muted); font-weight: 600; margin-left: 0.1rem; }
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

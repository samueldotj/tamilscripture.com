<script lang="ts">
	// Desktop context column (design 3A, tabbed in 8A): related verses for the
	// selection and the Study Bible aids, one tab each rather than stacked, and
	// the verse actions underneath. Rendered permanently on wide screens so
	// opening it pushes nothing around.
	import type { Snippet } from 'svelte';
	import type { XrefTarget } from '$lib/content/types';
	import XrefList from './XrefList.svelte';

	export type AidId = 'map' | 'places' | 'persons';
	export type TabId = 'related' | AidId;
	export interface Aid {
		id: AidId;
		ta: string;
		en: string;
		/** Shown on the tab when there is something to count. */
		n?: number;
	}

	let {
		label = '',
		targets = null,
		xrefsEnabled = true,
		version,
		lang,
		aids = [],
		tab = $bindable('related'),
		study,
		actions
	}: {
		/** verse or range label for the header; empty when nothing is selected */
		label?: string;
		targets?: XrefTarget[] | null;
		xrefsEnabled?: boolean;
		version: string;
		lang: 'ta' | 'en';
		/** Aids to offer as tabs, in order; empty when the chapter has none. */
		aids?: Aid[];
		/** Which tab is in view; bound so the page can fetch what a tab needs. */
		tab?: TabId;
		/** Renders one aid, named by the tab in view. */
		study?: Snippet<[AidId]>;
		actions?: Snippet;
	} = $props();

	const ta = $derived(lang === 'ta');
	// Related verses belong to a selection, so the tab only exists while a verse
	// is selected. With nothing selected the panel opens on the first aid, and
	// goes back to Related when a verse is picked, if that is where it was.
	const hasRelated = $derived(!!label);
	let leftRelated = false;
	$effect(() => {
		if (tab === 'related' && !hasRelated && aids.length) {
			// Not the map: it fetches the map engine, and nobody asked for it yet.
			tab = (aids.find((a) => a.id !== 'map') ?? aids[0]).id;
			leftRelated = true;
		} else if (hasRelated && leftRelated) {
			tab = 'related';
			leftRelated = false;
		} else if (tab !== 'related' && !aids.some((a) => a.id === tab)) {
			// An aid can go away under you (Places off in settings, or a chapter
			// that names none). Fall back rather than show an empty tab.
			tab = 'related';
		}
	});
</script>

<div class="context">
	<header>
		{#if label}
			<h2 lang={ta ? 'ta' : 'en'}>{label}</h2>
		{:else}
			<h2 class="empty" lang={ta ? 'ta' : 'en'}>{ta ? 'வசனம் தேர்வு செய்யவில்லை' : 'No verse selected'}</h2>
		{/if}
	</header>

	{#if aids.length}
		<div class="tabs" role="tablist" aria-label={ta ? 'சூழல்' : 'Context'}>
			{#if hasRelated}
				<button type="button" role="tab" class="tab" class:on={tab === 'related'} aria-selected={tab === 'related'} onclick={() => { tab = 'related'; leftRelated = false; }} lang={ta ? 'ta' : 'en'}>
					{ta ? 'தொடர்பு' : 'Related'}{#if targets?.length}<span class="tn">{targets.length}</span>{/if}
				</button>
			{/if}
			{#each aids as a (a.id)}
				<button type="button" role="tab" class="tab" class:on={tab === a.id} aria-selected={tab === a.id} onclick={() => (tab = a.id)} lang={ta ? 'ta' : 'en'}>
					{ta ? a.ta : a.en}{#if a.n}<span class="tn">{a.n}</span>{/if}
				</button>
			{/each}
		</div>
	{:else if hasRelated}
		<div class="kicker solo" lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'}{#if targets?.length} <span class="n">· {targets.length} {ta ? 'குறிப்புகள்' : 'refs'}</span>{/if}</div>
	{/if}

	<div class="body" class:fill={tab === 'map'}>
		{#if tab !== 'related' && study}
			{@render study(tab)}
		{:else if !label}
			<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒரு வசன எண்ணைத் தொட்டால் அதன் தொடர்புள்ள வசனங்கள் இங்கே காட்டப்படும். அடிக்கோடிட, குறிப்பு எழுத, நகலெடுக்க, பகிர இங்கேயே செய்யலாம்.' : 'Tap a verse number to see its related verses here, and to highlight, note, copy or share it.'}</p>
		{:else if !xrefsEnabled}
			<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒப்புவசனங்கள் அமைப்புகளில் அணைக்கப்பட்டுள்ளன.' : 'Cross-references are switched off in settings.'}</p>
		{:else if targets?.length}
			<XrefList {targets} {version} {lang} />
		{:else}
			<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த வசனத்திற்கு தொடர்புள்ள வசனங்கள் பட்டியலிடப்படவில்லை.' : 'No related verses are listed for this verse.'}</p>
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
	header { padding: 1.4rem 1.4rem 0.7rem; }
	/* One tab per thing the panel can show, instead of stacking them (8A). */
	.tabs { display: flex; gap: 0.25rem; padding: 0 1.4rem; border-bottom: var(--bw) solid var(--line); overflow-x: auto; scrollbar-width: none; }
	.tabs::-webkit-scrollbar { display: none; }
	.tab { font: inherit; font-size: 0.85rem; font-weight: 600; color: var(--muted); background: none; border: 0; border-bottom: 2px solid transparent; padding: 0.45rem 0.55rem 0.5rem; cursor: pointer; white-space: nowrap; display: inline-flex; align-items: center; gap: 0.3rem; min-height: 40px; }
	.tab[lang='ta'] { font-family: var(--tamil); }
	.tab:hover { color: var(--ink); }
	.tab.on { color: var(--accent); border-bottom-color: var(--accent); }
	.tn { font-size: 0.72rem; font-weight: 700; color: var(--muted); }
	.tab.on .tn { color: var(--accent); }
	.kicker.solo { padding: 0 1.4rem 0.8rem; border-bottom: var(--bw) solid var(--line); }
	h2 { font-size: 1.2rem; margin: 0.15rem 0 0; font-weight: 600; }
	h2[lang='ta'] { font-family: var(--tamil); }
	h2.empty { color: var(--muted); font-weight: 500; font-size: 1.05rem; }
	.n { font-size: 0.8rem; color: var(--muted); font-weight: 400; font-family: var(--sans); }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.body { flex: 1; padding: 0.6rem 1.4rem 1.4rem; }
	/* The Map tab fills the column: its map takes the height that is left. */
	.body.fill { display: flex; flex-direction: column; min-height: 0; }
	.body.fill > :global(.study) { flex: 1; min-height: 0; }
	.hint { color: var(--muted); line-height: 1.7; margin: 0.8rem 0 0; font-size: 0.95rem; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	footer { position: sticky; bottom: 0; padding: 1rem 1.4rem; border-top: var(--bw) solid var(--line); background: var(--surface); }
</style>

<script lang="ts">
	// Hides or shows the wide-screen book rail (rail-off on <html>). It sits in
	// the rail's own header; while the rail is hidden the reader floats one at
	// the left edge to bring it back.
	import { settings } from '$lib/settings/store.svelte';

	let { lang, floating = false }: { lang: 'ta' | 'en'; floating?: boolean } = $props();

	const ta = $derived(lang === 'ta');
	const label = $derived(floating ? (ta ? 'புத்தகப் பட்டியலைக் காட்டு' : 'Show book list') : ta ? 'புத்தகப் பட்டியலை மறை' : 'Hide book list');
</script>

<button type="button" class="rail-toggle" class:floating aria-expanded={!floating} aria-label={label} title={label} onclick={() => settings.update({ railCollapsed: !floating })}>
	<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
		<rect x="3" y="4" width="18" height="16" rx="2.5" /><path d="M9 4v16" />
		{#if floating}<path d="m13 9.5 2.5 2.5-2.5 2.5" />{:else}<path d="m15.5 9.5-2.5 2.5 2.5 2.5" />{/if}
	</svg>
</button>

<style>
	.rail-toggle { flex: none; display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; padding: 0; border: 0; border-radius: 10px; background: transparent; color: var(--muted); cursor: pointer; }
	.rail-toggle:hover { color: var(--accent); background: var(--surface); }
	.rail-toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
	.floating { position: fixed; z-index: 12; left: 12px; top: calc(var(--header-h, 0px) + 1.5rem); border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); box-shadow: var(--shadow); }
</style>

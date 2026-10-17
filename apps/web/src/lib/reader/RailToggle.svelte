<script lang="ts">
	// Hides or shows a side column: the book rail (left) or the context panel
	// (right). It sits in the column's own header; while the column is hidden
	// the reader floats one at that edge to bring it back. The reader decides
	// what showing means: a column on wide screens, a drawer over the text on
	// tablets.
	let {
		lang,
		side = 'rail',
		floating = false,
		ontoggle
	}: { lang: 'ta' | 'en'; side?: 'rail' | 'panel'; floating?: boolean; ontoggle: (show: boolean) => void } = $props();

	const ta = $derived(lang === 'ta');
	const label = $derived(
		side === 'rail'
			? floating ? (ta ? 'புத்தகப் பட்டியலைக் காட்டு' : 'Show book list') : ta ? 'புத்தகப் பட்டியலை மறை' : 'Hide book list'
			: floating ? (ta ? 'பக்கப் பலகையைக் காட்டு' : 'Show side panel') : ta ? 'பக்கப் பலகையை மறை' : 'Hide side panel'
	);
</script>

<button type="button" class="rail-toggle {side}" class:floating aria-expanded={!floating} aria-label={label} title={label} onclick={() => ontoggle(floating)}>
	<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
		<!-- The panel's icon is the rail's, mirrored; the chevron points the way the column will move. -->
		<g transform={side === 'panel' ? 'matrix(-1 0 0 1 24 0)' : undefined}>
			<rect x="3" y="4" width="18" height="16" rx="2.5" /><path d="M9 4v16" />
			{#if floating}<path d="m13 9.5 2.5 2.5-2.5 2.5" />{:else}<path d="m15.5 9.5-2.5 2.5 2.5 2.5" />{/if}
		</g>
	</svg>
</button>

<style>
	.rail-toggle { flex: none; display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; padding: 0; border: 0; border-radius: 10px; background: transparent; color: var(--muted); cursor: pointer; }
	.rail-toggle:hover { color: var(--accent); background: var(--surface); }
	.rail-toggle.panel:hover { background: var(--surface-2); }
	.rail-toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
	.floating { position: fixed; z-index: 12; top: calc(var(--header-h, 0px) + 1.5rem); border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); box-shadow: var(--shadow); }
	.floating.rail { left: 12px; }
	.floating.panel { right: 12px; }
</style>

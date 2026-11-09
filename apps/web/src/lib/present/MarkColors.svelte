<script lang="ts">
	// The highlight colour picker: a row of swatches, used under the editor's
	// preview and in the presenter's control pill. Keys 1–5 pick a colour in
	// the presenter's highlight mode.
	import { MARK_COLORS, type MarkColor } from './types';

	let { value = $bindable(), lang = 'ta', keys = false }: { value: MarkColor; lang?: string; keys?: boolean } = $props();
	const ta = $derived(lang === 'ta');
</script>

<div class="colors" role="radiogroup" aria-label={ta ? 'முன்னிலை நிறம்' : 'Highlight colour'}>
	{#each MARK_COLORS as c, n (c.id)}
		<button
			type="button"
			role="radio"
			aria-checked={value === c.id}
			class:on={value === c.id}
			style:--c={c.swatch}
			title={`${ta ? c.ta : c.en}${keys ? ` (${n + 1})` : ''}`}
			aria-label={ta ? c.ta : c.en}
			onclick={() => (value = c.id)}
		></button>
	{/each}
</div>

<style>
	.colors { display: inline-flex; align-items: center; gap: 6px; }
	button { width: 22px; height: 22px; border-radius: 50%; border: 2px solid transparent; background: var(--c); padding: 0; cursor: pointer; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.25); }
	button.on { border-color: currentColor; box-shadow: 0 0 0 2px var(--c); }
	button:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
</style>

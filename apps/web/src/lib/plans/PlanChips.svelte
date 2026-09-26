<script lang="ts">
	// The joined plans as chips, to switch the plan on Today and Stats.
	import { settings } from '$lib/settings/store.svelte';
	import { plansStore } from './store.svelte';
	import { stats } from './schedule';

	let { pct = false }: { pct?: boolean } = $props();
	const lang = $derived(settings.value.uiLang);
</script>

{#if plansStore.joined.length > 1}
	<div class="chips" role="group" aria-label={lang === 'ta' ? 'என் திட்டங்கள்' : 'My plans'}>
		{#each plansStore.joined as p (p.id)}
			{@const on = p.id === plansStore.active?.id}
			<button type="button" class:on aria-pressed={on} lang={lang} onclick={() => plansStore.pick(p.id)}>
				{p.title[lang]}{#if pct}{' · '}{stats(p, plansStore.progress(p.id)!).pct}%{/if}
			</button>
		{/each}
	</div>
{/if}

<style>
	.chips { display: flex; gap: 0.5rem; flex-wrap: wrap; }
	button { padding: 0.45rem 0.9rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600; cursor: pointer; background: transparent; color: var(--muted); border: var(--bw) solid var(--line-2); }
	button[lang='ta'] { font-family: var(--tamil); }
	button:hover { color: var(--ink); }
	button.on { background: var(--surface-3); color: var(--ink); border-color: var(--accent); }
</style>

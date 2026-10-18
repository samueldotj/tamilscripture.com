<script lang="ts">
	// A band of the home page below the book list: what the features are, then
	// two of them side by side (stacked on a phone).
	import type { Snippet } from 'svelte';

	let { id, kickerTa, kickerEn, title, lang, children }: {
		id: string; kickerTa: string; kickerEn: string; title: string; lang: 'ta' | 'en'; children: Snippet;
	} = $props();
</script>

<section class="band" aria-labelledby="{id}-h">
	<div class="intro">
		<p class="kicker"><span lang="ta">{kickerTa}</span> · {kickerEn}</p>
		<h2 id="{id}-h" {lang}>{title}</h2>
	</div>
	<div class="row">{@render children()}</div>
</section>

<style>
	.band { margin-top: 3.5rem; padding-top: 2.8rem; border-top: var(--bw) solid var(--line); display: flex; flex-direction: column; gap: 1.6rem; }
	.intro { display: flex; flex-direction: column; gap: 0.4rem; max-width: 46rem; }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; }
	h2 { margin: 0; font-size: 1.75rem; font-weight: 600; line-height: 1.3; }
	h2[lang='ta'] { font-family: var(--tamil); }
	.row { display: flex; flex-wrap: wrap; gap: 1.2rem; }
	@media (max-width: 480px) {
		.band { margin-top: 2.5rem; padding-top: 2rem; }
		h2 { font-size: 1.4rem; }
	}
</style>

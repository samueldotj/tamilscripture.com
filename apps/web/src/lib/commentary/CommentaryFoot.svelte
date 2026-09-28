<script lang="ts">
	// The provenance strip under a comment (design 15): the commentary and its
	// year, whether the text shown is the English original or a Tamil draft,
	// and the licence it is used under.
	import Provenance from '$lib/community/Provenance.svelte';
	import type { CommentarySource, CommentaryUnit } from './load';

	let { source, unit = null, lang }: { source: CommentarySource; unit?: CommentaryUnit | null; lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');
	const hasTa = $derived(!!unit?.paragraphs.some((p) => p.ta));
	const corrections = $derived(unit?.paragraphs.filter((p) => p.ta_source === 'community' || p.ta_source === 'owner').length ?? 0);
</script>

<div class="foot">
	<div class="meta">
		<span class="name">{source.name}, {source.year}</span>
		<span class="state" lang={ta ? 'ta' : 'en'}>
			{#if hasTa && ta}
				தமிழாக்கம் ·
				{#if corrections}<span class="ok">✓ {corrections} சமூக திருத்தங்கள்</span>{:else}<Provenance kind="draft" {lang} />{/if}
			{:else if ta}
				ஆங்கில மூலம் · <span class="soon">தமிழாக்கம் விரைவில்</span>
			{:else}
				English original{#if hasTa} · Tamil translation available in த{/if}
			{/if}
		</span>
	</div>
	<p class="attr">{source.attribution}. {source.licence}.</p>
</div>

<style>
	.foot { display: grid; gap: 0.35rem; padding: 0.7rem 0.8rem; background: var(--surface-2); border-radius: 10px; }
	.meta { display: grid; gap: 0.1rem; }
	.name { font-size: 0.82rem; font-weight: 700; }
	.state { font-size: 0.78rem; color: var(--muted); }
	.state[lang='ta'] { font-family: var(--tamil); }
	.ok { color: var(--good); font-weight: 600; }
	.soon { color: var(--amber); font-weight: 600; }
	.attr { margin: 0; font-size: 0.72rem; color: var(--muted); line-height: 1.5; }
</style>

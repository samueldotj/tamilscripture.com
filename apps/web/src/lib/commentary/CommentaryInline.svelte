<script lang="ts">
	// Inline under the verses (design 15C): a comment folds open beneath the
	// paragraph that ends its verses. Phones and tablets; wide screens have the
	// focus pane in the context panel instead.
	import CommentaryText from './CommentaryText.svelte';
	import { unitLabel, type CommentarySource, type CommentaryUnit } from './load';

	let {
		unit,
		source,
		chapter,
		lang,
		versionPath,
		open,
		ontoggle
	}: {
		unit: CommentaryUnit;
		source: CommentarySource;
		chapter: number;
		lang: 'ta' | 'en';
		versionPath: string;
		open: boolean;
		ontoggle: () => void;
	} = $props();
	const ta = $derived(lang === 'ta');
	const label = $derived(unit.kind === 'passage' ? `${ta ? 'வ.' : 'v.'} ${unitLabel(unit, chapter).split(':')[1]}` : ta ? 'அதிகார முன்னுரை' : 'Chapter introduction');
</script>

<div class="cm-inline" class:open>
	<button type="button" class="bar" aria-expanded={open} onclick={ontoggle}>
		<span class="badge">{source.short}</span>
		<span class="what" lang={ta ? 'ta' : 'en'}>{ta ? 'விளக்கவுரை' : 'Commentary'} · {label}</span>
		<span class="caret" lang={ta ? 'ta' : 'en'}>{open ? (ta ? 'மறை ▴' : 'Hide ▴') : ta ? 'காட்டு ▾' : 'Show ▾'}</span>
	</button>
	{#if open}
		<div class="text">
			{#if unit.title}<div class="title" lang={ta && unit.title_ta ? 'ta' : 'en'}>{ta && unit.title_ta ? unit.title_ta : unit.title}</div>{/if}
			<CommentaryText {unit} {lang} {versionPath} compact />
		</div>
	{/if}
</div>

<style>
	.cm-inline { margin: 0 0 1.4rem 1.4rem; border-radius: 14px; background: var(--surface); border: var(--bw) solid var(--line); overflow: hidden; font-family: var(--sans); font-size: 1rem; line-height: 1.6; }
	.bar { display: flex; align-items: center; gap: 0.6rem; width: 100%; padding: 0.65rem 1rem; border: 0; background: none; color: inherit; font: inherit; cursor: pointer; text-align: left; min-height: 44px; }
	.bar:hover { background: var(--surface-2); }
	.badge { font-size: 0.72rem; font-weight: 800; color: var(--on-accent); background: var(--accent); border-radius: 6px; padding: 0.1rem 0.45rem; }
	.what { font-size: 0.82rem; font-weight: 600; color: var(--ink-2); }
	.what[lang='ta'], .caret[lang='ta'] { font-family: var(--tamil); }
	.caret { margin-left: auto; font-size: 0.8rem; color: var(--muted); }
	.text { padding: 0 1rem 1rem; display: grid; gap: 0.6rem; }
	.title { font-weight: 700; color: var(--amber); font-size: 0.92rem; }
	.title[lang='ta'] { font-family: var(--tamil); }
	@media (max-width: 720px) {
		.cm-inline { margin-left: 0.6rem; }
	}
</style>

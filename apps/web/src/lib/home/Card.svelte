<script lang="ts">
	// One feature sample on the home page: its name in both languages, an
	// optional tag (the verse or item shown), the sample, and a link to the feature.
	import type { Snippet } from 'svelte';
	import { visible } from './visible';

	let { ta, en, tag, href, cta, lang, onvisible, children }: {
		ta: string; en: string; tag?: string; href: string; cta: string; lang: 'ta' | 'en';
		onvisible?: () => void; children: Snippet;
	} = $props();
</script>

<article class="card" use:visible={() => onvisible?.()}>
	<div class="top">
		<h3><span lang="ta">{ta}</span> <span class="en" lang="en">{en}</span></h3>
		{#if tag}<span class="tag" {lang}>{tag}</span>{/if}
	</div>
	{@render children()}
	<a class="more" {href} {lang}>{cta} <span aria-hidden="true">→</span></a>
</article>

<style>
	.card { flex: 1 1 26rem; min-width: 0; display: flex; flex-direction: column; gap: 1.1rem; padding: 1.4rem; border: var(--bw) solid var(--line); border-radius: var(--r-xl); background: var(--surface); box-sizing: border-box; }
	.top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.4rem 1rem; flex-wrap: wrap; }
	h3 { margin: 0; font-size: 1.22rem; font-weight: 600; }
	h3 [lang='ta'] { font-family: var(--tamil); }
	.en { font-size: 0.85rem; color: var(--muted); font-weight: 600; }
	.tag { font-size: 0.85rem; font-weight: 600; color: var(--amber); }
	.more { margin-top: auto; display: inline-flex; align-items: center; gap: 0.45rem; min-height: 44px; font-weight: 600; text-decoration: none; align-self: flex-start; }
	[lang='ta'].tag, [lang='ta'].more { font-family: var(--tamil); }
	.more:hover { text-decoration: underline; text-underline-offset: 3px; }
</style>

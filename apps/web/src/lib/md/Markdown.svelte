<script lang="ts">
	// Renders Markdown notes as elements from the tree parse.ts produces: no
	// HTML string, nothing to sanitise. Verse references in the text become
	// links with the site's hover preview (RefText).
	import RefText from '$lib/refs/RefText.svelte';
	import { parseMarkdown, type Block, type Inline } from './parse';

	let { source, version, lang }: { source: string; version?: string; lang?: 'ta' | 'en' } = $props();
	const blocks = $derived(parseMarkdown(source));
</script>

{#snippet inlines(list: Inline[])}
	{#each list as n, i (i)}
		{#if n.t === 'text'}<RefText text={n.s} {version} />{:else if n.t === 'strong'}<strong>{@render inlines(n.c)}</strong>{:else if n.t === 'em'}<em>{@render inlines(n.c)}</em>{:else if n.t === 'code'}<code>{n.s}</code>{:else if n.t === 'link'}<a href={n.href} rel="noopener" target={/^https?:/i.test(n.href) ? '_blank' : undefined}>{@render inlines(n.c)}</a>{:else}<br />{/if}
	{/each}
{/snippet}

{#snippet blockList(list: Block[])}
	{#each list as b, i (i)}
		{#if b.t === 'h'}
			<svelte:element this={`h${b.level + 1}`} class="h h{b.level}">{@render inlines(b.c)}</svelte:element>
		{:else if b.t === 'p'}
			<p>{@render inlines(b.c)}</p>
		{:else if b.t === 'quote'}
			<blockquote>{@render blockList(b.c)}</blockquote>
		{:else if b.t === 'list'}
			{#if b.ordered}
				<ol>{#each b.items as item, j (j)}<li>{@render blockList(item)}</li>{/each}</ol>
			{:else}
				<ul>{#each b.items as item, j (j)}<li>{@render blockList(item)}</li>{/each}</ul>
			{/if}
		{:else}
			<hr />
		{/if}
	{/each}
{/snippet}

<div class="md" {lang}>{@render blockList(blocks)}</div>

<style>
	/* Sizes are relative so the same notes read well in the editor, on a slide
	   and in a list: the host sets font-size. */
	.md { line-height: 1.6; overflow-wrap: anywhere; }
	.md > :first-child { margin-top: 0; }
	.md > :last-child { margin-bottom: 0; }
	p { margin: 0 0 0.6em; }
	.h { margin: 0.9em 0 0.4em; font-weight: 600; line-height: 1.3; text-wrap: balance; color: var(--md-heading, inherit); }
	.h1 { font-size: 1.35em; }
	.h2 { font-size: 1.2em; }
	.h3 { font-size: 1.05em; }
	strong { font-weight: 700; color: var(--md-strong, inherit); }
	code { font-size: 0.9em; padding: 0.05em 0.3em; border-radius: 4px; background: var(--md-code-bg, rgba(127, 127, 127, 0.15)); }
	blockquote { margin: 0.6em 0; padding: 0.1em 0 0.1em 0.8em; border-left: 3px solid var(--md-rule, var(--accent)); color: var(--md-quote, var(--muted)); font-style: italic; }
	ul, ol { margin: 0 0 0.6em; padding-left: 1.3em; }
	li { margin: 0.15em 0; }
	li > p { margin: 0; }
	li ul, li ol { margin: 0.15em 0 0; }
	hr { border: 0; border-top: 1px solid var(--md-rule, var(--line)); margin: 0.9em 0; }
	a { color: var(--md-link, var(--accent)); }
</style>

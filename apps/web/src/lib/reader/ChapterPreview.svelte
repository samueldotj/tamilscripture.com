<script lang="ts">
	// Continuous scrolling (the app does the same): the next chapter's first verses after
	// this one, or the previous chapter's last verses before it, greyed. Scrolling on into
	// them opens that chapter in place (ChapterPage). Plain text: nothing here is tappable.
	import type { ChapterJson } from '$lib/content/types';

	let { chapter, part, title, lang, rows = 4, titleEl = $bindable() }: {
		chapter: ChapterJson;
		/** 'start': the chapter's first rows (the next chapter); 'end': its last (the previous). */
		part: 'start' | 'end';
		/** "மத்தேயு 3". */
		title: string;
		lang: string;
		/** How many verses. */
		rows?: number;
		titleEl?: HTMLElement;
	} = $props();

	type Row = { kind: 'heading'; text: string } | { kind: 'para'; parts: { n?: string; text: string }[] };

	/** Headings and paragraphs, a paragraph's verses run together with their numbers. */
	const all = $derived.by((): Row[] => {
		const out: Row[] = [];
		for (const b of chapter.blocks) {
			if (b.type === 'heading') out.push({ kind: 'heading', text: b.text });
			else if (b.type === 'para' && b.segments.length) out.push({ kind: 'para', parts: b.segments.map((s) => ({ n: s.n, text: s.text })) });
		}
		return out;
	});
	/** The first (or last) [rows] verses, in their paragraphs: a long paragraph is cut, not shown whole. */
	const shown = $derived.by((): Row[] => {
		const out: Row[] = [];
		let left = rows;
		const seq = part === 'start' ? all : [...all].reverse();
		for (const r of seq) {
			if (left <= 0) break;
			if (r.kind === 'heading') { out.push(r); continue; }
			const parts = part === 'start' ? r.parts : [...r.parts].reverse();
			const kept: typeof r.parts = [];
			for (const p of parts) {
				if (left <= 0) break;
				kept.push(p);
				if (p.n) left--;
			}
			out.push({ kind: 'para', parts: part === 'start' ? kept : kept.reverse() });
		}
		return part === 'start' ? out : out.reverse();
	});
</script>

<section class="preview {part}" {lang} aria-hidden="true" inert>
	{#if part === 'start'}
		<hr />
		<h2 class="pv-title" bind:this={titleEl}>{title}</h2>
	{:else}
		<p class="pv-kicker">{title}</p>
	{/if}
	{#each shown as r, i (i)}
		{#if r.kind === 'heading'}
			<p class="pv-heading">{r.text}</p>
		{:else}
			<p class="pv-para">{#each r.parts as p, j (j)}{#if p.n}<sup>{p.n}</sup>{/if}{p.text}{' '}{/each}</p>
		{/if}
	{/each}
	{#if part === 'end'}<hr />{/if}
</section>

<style>
	.preview { max-width: var(--measure, 40rem); overflow-wrap: break-word; color: var(--muted); opacity: 0.55; user-select: none; }
	.preview[lang='ta'] { font-family: var(--tamil); font-size: 1.3rem; line-height: 1.9; }
	.preview[lang='en'] { font-family: var(--en); font-size: 1.12rem; line-height: 1.8; }
	.preview.start { margin-top: 2.5rem; }
	.preview.end { margin-bottom: 2rem; }
	hr { border: 0; border-top: var(--bw) solid var(--line); margin: 1.5rem 0; }
	.pv-title { font-size: 1.6rem; margin: 0 0 0.8rem; font-weight: 600; line-height: 1.3; }
	.pv-kicker { font-family: var(--sans); font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; margin: 0 0 0.5rem; }
	.preview[lang='ta'] .pv-kicker { font-family: var(--tamil); letter-spacing: 0; text-transform: none; }
	.pv-heading { font-weight: 600; font-size: 1.06rem; margin: 1.2em 0 0.5em; }
	.pv-para { margin: 0 0 1em; text-wrap: pretty; }
	sup { font-family: var(--sans); font-size: 0.6em; font-weight: 700; margin-right: 0.25em; }
</style>

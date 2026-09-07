<script lang="ts">
	import type { ChapterJson, Segment, XrefChapter } from '$lib/content/types';
	import Verse from './Verse.svelte';

	let {
		chapter,
		lang,
		selected = new Set<string>(),
		onselect,
		xrefs = null,
		onxref,
		versionPath = 'irvtam',
		highlights = new Map<string, string>(),
		noted = new Set<string>(),
		onnote
	}: {
		chapter: ChapterJson;
		lang: 'ta' | 'en';
		selected?: Set<string>;
		onselect?: (id: string) => void;
		xrefs?: XrefChapter | null;
		onxref?: (id: string) => void;
		versionPath?: string;
		/** verse id → highlight colour */
		highlights?: Map<string, string>;
		/** verse ids that carry a user note */
		noted?: Set<string>;
		onnote?: (id: string) => void;
	} = $props();

	// Footnotes numbered across the chapter for the list at the end.
	const notes = $derived.by(() => {
		const out: { n: number; id: string; seg: Segment; note: NonNullable<Segment['notes']>[number] }[] = [];
		let n = 0;
		for (const b of chapter.blocks) {
			if (b.type !== 'para') continue;
			for (const seg of b.segments) {
				for (const note of seg.notes ?? []) {
					n += 1;
					out.push({ n, id: `${chapter.book}.${chapter.chapter}.n${n}`, seg, note });
				}
			}
		}
		return out;
	});
	const noteStarts = $derived.by(() => {
		const map = new Map<Segment, number>();
		let i = 0;
		for (const b of chapter.blocks) {
			if (b.type !== 'para') continue;
			for (const seg of b.segments) {
				map.set(seg, i);
				i += seg.notes?.length ?? 0;
			}
		}
		return map;
	});
</script>

<article class="chapter" {lang} data-version={chapter.version} data-book={chapter.book} data-chapter={chapter.chapter}>
	{#if chapter.label}<div class="chapter-label">{chapter.label}</div>{/if}
	{#each chapter.blocks as block, i (i)}
		{#if block.type === 'heading'}
			{#if block.kind === 'r' || block.kind === 'mr' || block.kind === 'sr'}
				<p class="heading ref">{block.text}</p>
			{:else if block.kind === 'sp'}
				<p class="heading speaker">{block.text}</p>
			{:else if block.kind === 'ms'}
				<h2 class="heading major">{block.text}</h2>
			{:else}
				<h3 class="heading level-{block.level}">{block.text}</h3>
			{/if}
		{:else if block.type === 'break'}
			<div class="blank" aria-hidden="true"></div>
		{:else}
			<p class="para style-{block.style}">
				{#each block.segments as seg (seg.id ?? `${i}-${seg.text.slice(0, 8)}`)}
					<Verse
						{seg}
						{onselect}
						{lang}
						{versionPath}
						selected={seg.id !== undefined && selected.has(seg.id)}
						noteStart={noteStarts.get(seg) ?? 0}
						xrefs={seg.n && seg.id && xrefs ? xrefs[seg.id] ?? null : null}
						{onxref}
						highlight={seg.id ? highlights.get(seg.id) ?? null : null}
						hasNote={seg.id !== undefined && noted.has(seg.id)}
						{onnote}
					/>
				{/each}
			</p>
		{/if}
	{/each}

	{#if notes.length}
		<aside class="footnotes" aria-label={lang === 'ta' ? 'அடிக்குறிப்புகள்' : 'Footnotes'}>
			<ol>
				{#each notes as { n, id, note } (id)}
					<li {id}><span class="fn-ref">{note.reference}</span> {note.text}</li>
				{/each}
			</ol>
		</aside>
	{/if}
</article>

<style>
	.chapter { max-width: 42rem; }
	.chapter[lang='ta'] { font-family: var(--tamil); font-size: 1.05rem; line-height: 1.9; }
	.chapter[lang='en'] { font-family: var(--serif); font-size: 1.05rem; line-height: 1.7; }
	.chapter-label { display: none; }
	.heading { font-family: var(--sans); font-weight: 600; margin: 1.6em 0 0.5em; line-height: 1.3; }
	.chapter[lang='ta'] .heading { font-family: var(--tamil); }
	h3.heading { font-size: 1.05rem; }
	h2.heading.major { font-size: 1.2rem; text-transform: uppercase; letter-spacing: 0.04em; }
	.heading.ref { font-size: 0.85rem; color: var(--muted); font-weight: 400; margin-top: 0; }
	.heading.speaker { font-style: italic; font-weight: 400; margin-bottom: 0; }
	.para { margin: 0 0 0.9em; }
	.style-q1, .style-qm1 { margin: 0; padding-left: 1.5em; text-indent: -1.5em; }
	.style-q2, .style-qm2 { margin: 0; padding-left: 3em; text-indent: -1.5em; }
	.style-q3 { margin: 0; padding-left: 4.5em; text-indent: -1.5em; }
	.style-qr { margin: 0; text-align: right; }
	.style-qc, .style-pc { margin: 0 0 0.9em; text-align: center; }
	.style-m, .style-nb { text-indent: 0; }
	.style-mi, .style-pi1, .style-pm, .style-pmo, .style-pmc, .style-pr { margin-left: 1.5em; }
	.style-li1 { margin: 0; padding-left: 1.5em; }
	.style-li2 { margin: 0; padding-left: 3em; }
	.style-li3 { margin: 0; padding-left: 4.5em; }
	.style-li4 { margin: 0; padding-left: 6em; }
	.style-d { font-style: italic; color: var(--muted); }
	.blank { height: 0.9em; }
	.footnotes { margin-top: 2rem; font-size: 0.85rem; color: var(--muted); border-top: 1px solid var(--line); padding-top: 0.75rem; }
	.footnotes ol { padding-left: 1.5rem; margin: 0; }
	.fn-ref { font-weight: 600; }
</style>

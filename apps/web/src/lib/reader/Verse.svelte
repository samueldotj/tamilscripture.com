<script lang="ts">
	import type { Segment, XrefTarget } from '$lib/content/types';
	import { chapterUrl, findBook } from '$lib/content/manifest';

	let {
		seg,
		lang,
		versionPath = 'irvtam',
		noteStart = 0,
		selected = false,
		onselect,
		xrefs = null,
		onxref,
		highlight = null,
		hasNote = false,
		onnote,
		heat = 0,
		users = 0
	}: {
		seg: Segment;
		lang: 'ta' | 'en';
		versionPath?: string;
		noteStart?: number;
		selected?: boolean;
		onselect?: (id: string) => void;
		xrefs?: XrefTarget[] | null;
		onxref?: (id: string) => void;
		highlight?: string | null;
		hasNote?: boolean;
		onnote?: (id: string) => void;
		/** community heat bucket 0..4 (overlay) and raw user count (tooltip) */
		heat?: number;
		users?: number;
	} = $props();

	// Split the text into runs at span boundaries and note anchors so that
	// words-of-Jesus spans and footnote markers land at the right characters.
	type Run = { text: string; wj: boolean; noteAfter?: number };
	const runs = $derived.by(() => {
		const chars = Array.from(seg.text);
		const cuts = new Set<number>([0, chars.length]);
		for (const s of seg.spans ?? []) { cuts.add(s.start); cuts.add(s.end); }
		const noteAt = new Map<number, number[]>();
		(seg.notes ?? []).forEach((n, i) => {
			cuts.add(n.at);
			noteAt.set(n.at, [...(noteAt.get(n.at) ?? []), noteStart + i + 1]);
		});
		const points = [...cuts].sort((a, b) => a - b);
		const out: Run[] = [];
		for (let i = 0; i < points.length - 1; i++) {
			const [a, b] = [points[i], points[i + 1]];
			const wj = (seg.spans ?? []).some((s) => s.start <= a && b <= s.end);
			out.push({ text: chars.slice(a, b).join(''), wj });
		}
		for (const [at, nums] of noteAt) {
			const idx = points.indexOf(at);
			const target = idx > 0 ? out[idx - 1] : out[0];
			if (target) target.noteAfter = nums[0];
			for (const extra of nums.slice(1)) out.splice(out.indexOf(target) + 1, 0, { text: '', wj: false, noteAfter: extra });
		}
		if (out.length === 0 && noteAt.size) out.push({ text: '', wj: false, noteAfter: [...noteAt.values()][0][0] });
		return out;
	});
	const chapterId = $derived(seg.id?.split('.').slice(0, 2).join('.'));

	// Inline list for the Cross-reference format (CSS shows it only there).
	function xrefLabel(t: XrefTarget) {
		const [code, ch, v] = t.to.split('.');
		const book = findBook(code)!;
		const end = t.end?.split('.');
		const name = lang === 'ta' ? (book.abbr_ta[0] ?? book.name_ta) : (book.abbr_en[0] ?? book.name_en);
		return end && end[1] === ch ? `${name} ${ch}:${v}-${end[2]}` : `${name} ${ch}:${v}`;
	}
	function xrefHref(t: XrefTarget, version: string) {
		const [code, ch, v] = t.to.split('.');
		const book = findBook(code)!;
		const end = t.end?.split('.');
		return chapterUrl(version, book, Number(ch), end && end[1] === ch && end[2] !== v ? `${v}-${end[2]}` : v);
	}
</script>

<span class="verse {highlight ? `hl-${highlight}` : ''} {heat ? `heat-${heat}` : ''}" class:selected id={seg.n ? seg.id : undefined} data-verse={seg.id}>
	{#if seg.n}
		{#if onselect && seg.id}
			<button type="button" class="vn" aria-label="verse {seg.n}{users ? `, highlighted by ${users} readers` : ''}" title={users ? `${users} readers highlighted this verse` : undefined} aria-pressed={selected} onclick={() => onselect(seg.id!)}>{seg.n}</button>
		{:else}
			<sup class="vn" aria-label="verse {seg.n}">{seg.n}</sup>
		{/if}
	{/if}
	{#each runs as run, i (i)}
		{#if run.wj}<span class="wj">{run.text}</span>{:else}{run.text}{/if}
		{#if run.noteAfter}<sup class="fn"><a href="#{chapterId}.n{run.noteAfter}" aria-label="footnote {run.noteAfter}">{run.noteAfter}</a></sup>{/if}
	{/each}
	{#if hasNote && seg.n && seg.id}
		<button type="button" class="note-mark" aria-label={lang === 'ta' ? 'உங்கள் குறிப்பு' : 'Your note'} onclick={() => onnote?.(seg.id!)}>✎</button>
	{/if}
	{#if xrefs?.length && seg.id}
		<button type="button" class="xref" aria-label="{xrefs.length} cross-references" onclick={() => onxref?.(seg.id!)}>‡</button>
		<span class="xref-list" lang={lang}>
			{#each xrefs.slice(0, 8) as t (t.to + (t.end ?? ''))}
				<a href={xrefHref(t, versionPath)}>{xrefLabel(t)}</a>
			{/each}
			{#if xrefs.length > 8}<button type="button" class="xref-more" onclick={() => onxref?.(seg.id!)}>+{xrefs.length - 8}</button>{/if}
		</span>
	{/if}
</span>

<style>
	.verse { scroll-margin-top: 5rem; border-radius: 2px; }
	.verse.selected { background: var(--select); box-shadow: 0 0 0 3px var(--select); }
	.vn { font-family: var(--sans); font-size: 0.62em; color: var(--accent); margin-right: 0.15em; font-weight: 600; vertical-align: super; line-height: 1; }
	button.vn { border: 0; background: none; padding: 0.15em 0.2em; margin-left: -0.2em; cursor: pointer; border-radius: 3px; }
	button.vn:hover { background: var(--accent-soft); }
	.fn { font-family: var(--sans); font-size: 0.6em; }
	.fn a { color: var(--muted); text-decoration: none; }
	.wj { color: var(--wj); }
	.note-mark, .xref { border: 0; background: none; padding: 0 0.15em; margin-left: 0.1em; color: var(--muted); font-size: 0.7em; vertical-align: super; line-height: 1; cursor: pointer; font-family: var(--sans); }
	.note-mark { color: var(--accent); }
	.xref:hover, .note-mark:hover { color: var(--accent); }
	.xref-list { display: none; font-family: var(--sans); font-size: 0.78em; color: var(--muted); text-indent: 0; margin-top: 0.1em; }
	.xref-list a { color: var(--muted); text-decoration: none; margin-right: 0.7em; }
	.xref-list a:hover { color: var(--accent); }
	.xref-more { border: 0; background: none; color: var(--accent); cursor: pointer; padding: 0; font-size: inherit; }
</style>

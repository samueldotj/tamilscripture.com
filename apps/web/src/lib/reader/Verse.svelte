<script lang="ts">
	import type { Segment, XrefTarget } from '$lib/content/types';
	import { chapterUrl, DEFAULT_VERSION, findBook } from '$lib/content/manifest';
	import { splitNames, type NameHit, type VerseNames } from './names';
	import type { Mark, SideNote } from './marks';
	import type { Note } from '$lib/personal/repo';
	import Markdown from '$lib/md/Markdown.svelte';

	let {
		seg,
		lang,
		versionPath = DEFAULT_VERSION.toLowerCase(),
		noteStart = 0,
		selected = false,
		onselect,
		xrefs = null,
		onxref,
		highlight = null,
		hasNote = false,
		onnote,
		heat = 0,
		users = 0,
		names = null,
		onname,
		marks = null,
		sidenotes = null,
		onopennote
	}: {
		seg: Segment;
		lang: string;
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
		/** People and places to mark in this verse (the Dictionary words setting). */
		names?: VerseNames | null;
		onname?: (hit: NameHit) => void;
		/** Word-range highlights and notes in this verse (R-10.15). */
		marks?: Mark[] | null;
		/** The reader's notes that start in this verse, shown beside it; null when the setting is off. */
		sidenotes?: SideNote[] | null;
		onopennote?: (note: Note) => void;
	} = $props();

	function openName(e: MouseEvent, hit: NameHit) {
		// A plain link without script or with a modifier key; the card otherwise.
		if (!onname || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
		e.preventDefault();
		onname(hit);
	}

	// Split the text into runs at span boundaries and note anchors so that
	// words-of-Jesus spans and footnote markers land at the right characters,
	// and at word-range marks and margin-note anchors. Each run carries its
	// character offset (data-o) so a text selection maps back to offsets.
	type Run = { text: string; from: number; wj: boolean; noteAfter?: number; hl?: string; noted?: boolean; side?: SideNote[] };
	const runs = $derived.by(() => {
		const chars = Array.from(seg.text);
		const cuts = new Set<number>([0, chars.length]);
		for (const s of seg.spans ?? []) { cuts.add(s.start); cuts.add(s.end); }
		const clamp = (n: number) => Math.max(0, Math.min(chars.length, n));
		for (const m of marks ?? []) { cuts.add(clamp(m.from)); cuts.add(clamp(m.to)); }
		const anchor = (s: SideNote) => clamp(Math.min(s.at, chars.length - 1));
		for (const s of sidenotes ?? []) cuts.add(anchor(s));
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
			const over = (marks ?? []).filter((m) => m.from <= a && b <= m.to);
			const hl = over.filter((m) => m.color).at(-1)?.color;
			const side = (sidenotes ?? []).filter((s) => anchor(s) === a);
			out.push({ text: chars.slice(a, b).join(''), from: a, wj, hl, noted: over.some((m) => m.note), side: side.length ? side : undefined });
		}
		for (const [at, nums] of noteAt) {
			const idx = points.indexOf(at);
			const target = idx > 0 ? out[idx - 1] : out[0];
			if (target) target.noteAfter = nums[0];
			for (const extra of nums.slice(1)) out.splice(out.indexOf(target) + 1, 0, { text: '', from: target?.from ?? 0, wj: false, noteAfter: extra });
		}
		if (out.length === 0 && noteAt.size) out.push({ text: '', from: 0, wj: false, noteAfter: [...noteAt.values()][0][0] });
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

{#snippet sidenote(s: SideNote, where: 'side' | 'below')}
	{@const n = s.note}
	<span class="mnote {where}" role="note">
		<button type="button" class="mnote-open" onclick={() => onopennote?.(n)} aria-label={lang === 'ta' ? `குறிப்பு, வசனம் ${n.verse_start}: திருத்து` : `Note on verse ${n.verse_start}: edit`}>✎ {n.verse_start}{n.verse_end !== n.verse_start ? `-${n.verse_end}` : ''}{#if n.quote}<span class="mnote-quote"> “{n.quote.length > 48 ? `${n.quote.slice(0, 48)}…` : n.quote}”</span>{/if}</button>
		<span class="mnote-body"><Markdown source={n.body} version={versionPath} /></span>
	</span>
{/snippet}

{#snippet text(t: string)}
	{#each splitNames(t, names) as piece, j (j)}
		{#if piece.hit}<a class="nm" href="/{piece.hit.kind}/{piece.hit.id}" onclick={(e) => openName(e, piece.hit!)}>{piece.t}</a>{:else}{piece.t}{/if}
	{/each}
{/snippet}

<span class="verse {highlight ? `hl-${highlight}` : ''} {heat ? `heat-${heat}` : ''}" class:selected id={seg.n ? seg.id : undefined} data-verse={seg.id}>
	{#if seg.n}
		{#if onselect && seg.id}
			<button type="button" class="vn" aria-label="verse {seg.n}{users ? `, highlighted by ${users} readers` : ''}" title={users ? `${users} readers highlighted this verse` : undefined} aria-pressed={selected} onclick={() => onselect(seg.id!)}>{seg.n}</button>
		{:else}
			<sup class="vn" aria-label="verse {seg.n}">{seg.n}</sup>
		{/if}
	{/if}
	<!-- One line: whitespace between runs would render as a space, and a mark can end mid-word. -->
	{#each runs as run, i (i)}{#each run.side ?? [] as s (s.note.id)}{@render sidenote(s, 'side')}{/each}<span data-o={run.from} class="{run.wj ? 'wj' : ''} {run.hl ? `mk hl-${run.hl}` : ''}" class:nu={run.noted}>{@render text(run.text)}</span>{#if run.noteAfter}<sup class="fn"><a href="#{chapterId}.n{run.noteAfter}" aria-label="footnote {run.noteAfter}">{run.noteAfter}</a></sup>{/if}{/each}
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
	{#each sidenotes ?? [] as s (s.note.id)}{@render sidenote(s, 'below')}{/each}
</span>

<style>
	.verse { scroll-margin-top: 6rem; border-radius: 2px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
	/* Selected verse: the design's amber block, bled 6px past the text box */
	.verse.selected { background: var(--hl); box-shadow: 0 0 0 6px var(--hl); }
	.vn { font-family: var(--sans); font-size: 0.58em; color: var(--accent); margin-right: 0.25em; font-weight: 700; vertical-align: super; line-height: 1; }
	button.vn { border: 0; background: none; padding: 0.15em 0.25em; margin-left: -0.25em; cursor: pointer; border-radius: 4px; }
	button.vn:hover { background: var(--accent-soft); }
	.fn { font-family: var(--sans); font-size: 0.6em; }
	.fn a { color: var(--muted); text-decoration: none; }
	.wj { color: var(--wj); }
	.note-mark, .xref { border: 0; background: none; padding: 0 0.15em; margin-left: 0.1em; color: var(--muted); font-size: 0.66em; vertical-align: super; line-height: 1; cursor: pointer; font-family: var(--sans); }
	.note-mark { color: var(--accent); }
	.xref:hover, .note-mark:hover { color: var(--accent); }
	/* Kept out of copied text: a copy holds the verse numbers and words only. */
	.note-mark, .xref, .xref-list { -webkit-user-select: none; user-select: none; }
	/* Dictionary words (7A): a dotted gold underline, nothing that moves the text. */
	.nm { color: inherit; text-decoration: underline dotted var(--amber); text-decoration-thickness: 1.5px; text-underline-offset: 0.28em; cursor: pointer; border-radius: 3px; }
	.nm:hover, .nm:focus-visible { background: var(--accent-soft); }
	.xref-list { display: none; font-family: var(--sans); font-size: 0.72em; color: var(--muted); text-indent: 0; margin-top: 0.1em; }
	.xref-list a { color: var(--muted); text-decoration: none; margin-right: 0.7em; }
	.xref-list a:hover { color: var(--accent); }
	/* Word-range highlights and notes (R-10.15): the colour behind the words, a
	   solid accent underline under words that carry a note. */
	.mk { border-radius: 2px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
	.mk.hl-yellow { background: var(--hl-yellow); }
	.mk.hl-green { background: var(--hl-green); }
	.mk.hl-blue { background: var(--hl-blue); }
	.mk.hl-pink { background: var(--hl-pink); }
	.nu { text-decoration: underline solid var(--accent); text-decoration-thickness: 1.5px; text-underline-offset: 0.3em; text-decoration-skip-ink: none; }
	/* The reader's own notes. Below the verse by default; in the margin, level
	   with the words they belong to, when the chapter frame has room (Chapter.svelte). */
	.mnote { display: none; text-indent: 0; text-align: left; font-family: var(--tamil); font-size: 0.66em; line-height: 1.55; color: var(--ink-2); font-style: normal; -webkit-user-select: none; user-select: none; }
	.mnote.below { margin: 0.35em 0 0.7em; padding: 0.45em 0.75em; border-left: 2px solid var(--accent); background: var(--surface-2); border-radius: 0 var(--r-s) var(--r-s) 0; }
	.mnote.side { float: right; clear: right; width: calc(var(--mw) - 1.25rem); margin: 0.35em calc(-1 * var(--mw)) 0.6em 0; padding: 0 0 0 0.7em; border-left: 2px solid var(--accent); }
	.mnote.below { display: block; }
	@container chapter (min-width: 41rem) {
		.mnote.below { display: none; }
		.mnote.side { display: block; }
	}
	.mnote-open { display: block; border: 0; background: none; padding: 0; margin: 0 0 0.15em; font: inherit; font-family: var(--sans); font-size: 0.85em; font-weight: 700; color: var(--accent); cursor: pointer; text-align: left; }
	.mnote-open:hover { text-decoration: underline; }
	.mnote-quote { font-weight: 400; font-style: italic; color: var(--muted); font-family: var(--tamil); }
	.mnote-body { display: block; overflow: hidden; }
	.side .mnote-body { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 8; line-clamp: 8; }
	.mnote-body :global(.md p) { margin: 0 0 0.3em; }
	.mnote-body :global(.md ul), .mnote-body :global(.md ol) { margin: 0 0 0.3em; padding-left: 1.2em; }
	.xref-more { border: 0; background: none; color: var(--accent); cursor: pointer; padding: 0; font-size: inherit; }
</style>

<script lang="ts">
	import type { Segment } from '$lib/content/types';

	let { seg, noteStart = 0, selected = false }: { seg: Segment; noteStart?: number; selected?: boolean } = $props();

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
		// Attach note markers to the run ending at their anchor.
		for (const [at, nums] of noteAt) {
			const idx = points.indexOf(at);
			const target = idx > 0 ? out[idx - 1] : out[0];
			if (target) target.noteAfter = nums[0];
			for (const extra of nums.slice(1)) out.splice(out.indexOf(target) + 1, 0, { text: '', wj: false, noteAfter: extra });
		}
		if (out.length === 0 && noteAt.size) out.push({ text: '', wj: false, noteAfter: [...noteAt.values()][0][0] });
		return out;
	});
</script>

<span class="verse" class:selected id={seg.n ? seg.id : undefined} data-verse={seg.id}>
	{#if seg.n}<sup class="vn" aria-label="verse {seg.n}">{seg.n}</sup>{/if}
	{#each runs as run, i (i)}
		{#if run.wj}<span class="wj">{run.text}</span>{:else}{run.text}{/if}
		{#if run.noteAfter}<sup class="fn"><a href="#{seg.id?.split('.').slice(0, 2).join('.')}.n{run.noteAfter}" aria-label="footnote {run.noteAfter}">{run.noteAfter}</a></sup>{/if}
	{/each}
</span>

<style>
	.verse { scroll-margin-top: 5rem; }
	.verse.selected { background: var(--select, rgba(126, 42, 42, 0.1)); box-shadow: 0 0 0 3px var(--select, rgba(126, 42, 42, 0.1)); border-radius: 2px; }
	.vn { font-family: var(--sans); font-size: 0.62em; color: var(--accent); margin-right: 0.15em; font-weight: 600; }
	.fn { font-family: var(--sans); font-size: 0.6em; }
	.fn a { color: var(--muted); text-decoration: none; }
	.wj { color: var(--wj); }
</style>

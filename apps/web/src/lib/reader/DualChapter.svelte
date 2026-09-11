<script lang="ts">
	// Two versions aligned verse by verse (R-9.1, R-9.2, R-9.4). Rows follow the
	// primary version's verse order; a verse missing from one side shows a dash.
	// Desktop: verse-locked columns with a shared number in the gutter (design
	// 3B). Narrow screens: one card per verse with both versions stacked (design 03).
	import type { ChapterJson, Segment, VersionMeta } from '$lib/content/types';
	import Verse from './Verse.svelte';

	let {
		chapters,
		versions,
		selected = new Set<string>(),
		onselect
	}: {
		chapters: ChapterJson[];
		versions: VersionMeta[];
		selected?: Set<string>;
		onselect?: (id: string) => void;
	} = $props();

	type Row = { id: string; n: string; heading?: string; cells: (Segment[] | null)[] };

	const rows = $derived.by(() => {
		// Collect segments per verse id per version, remembering headings that
		// precede a verse in the primary version.
		const perVersion = chapters.map((ch) => {
			const map = new Map<string, Segment[]>();
			const headings = new Map<string, string>();
			let pending: string[] = [];
			for (const b of ch.blocks) {
				if (b.type === 'heading' && (b.kind === 's' || b.kind === 'ms')) pending.push(b.text);
				if (b.type !== 'para') continue;
				for (const seg of b.segments) {
					if (!seg.id) continue;
					if (!map.has(seg.id)) {
						map.set(seg.id, []);
						if (pending.length) {
							headings.set(seg.id, pending.join(' · '));
							pending = [];
						}
					}
					map.get(seg.id)!.push(seg);
				}
			}
			return { map, headings };
		});
		const order: string[] = [];
		const seen = new Set<string>();
		for (const pv of perVersion) {
			for (const id of pv.map.keys()) {
				if (!seen.has(id)) { seen.add(id); order.push(id); }
			}
		}
		// Sort by verse number so extra verses from the second version land in place.
		order.sort((a, b) => Number(a.split('.')[2]) - Number(b.split('.')[2]));
		return order.map<Row>((id) => {
			const first = perVersion.map((pv) => pv.map.get(id)?.[0]).find(Boolean);
			return {
				id,
				n: first?.n ?? id.split('.')[2],
				heading: perVersion[0].headings.get(id),
				cells: perVersion.map((pv) => pv.map.get(id) ?? null)
			};
		});
	});
	const verseWord = $derived(versions[0].lang === 'ta' ? 'வசனம்' : 'Verse');
</script>

<div class="dual">
	<div class="head">
		<span class="gutter" aria-hidden="true"></span>
		{#each versions as v (v.code)}
			<div class="col">
				<span class="code">{v.short}</span>
				<span class="name" lang={v.lang}>{v.name_native}</span>
			</div>
		{/each}
	</div>
	{#each rows as row (row.id)}
		{#if row.heading}
			<h3 class="heading" lang={versions[0].lang}>{row.heading}</h3>
		{/if}
		<div class="row" class:selected={selected.has(row.id)} data-verse={row.id}>
			{#if onselect}
				<button type="button" class="gn" aria-pressed={selected.has(row.id)} aria-label="{verseWord} {row.n}" onclick={() => onselect(row.id)}>
					<span class="badge">{row.n}</span>
					<span class="word kicker">{verseWord} {row.n}</span>
				</button>
			{:else}
				<span class="gn"><span class="badge">{row.n}</span></span>
			{/if}
			{#each row.cells as cell, i (versions[i].code)}
				<div class="cell chapter" lang={versions[i].lang} class:missing={!cell}>
					{#if cell}
						{#each cell as seg, j (j)}
							<Verse {seg} lang={versions[i].lang} versionPath={versions[i].code.toLowerCase()} />
						{/each}
					{:else}
						<span class="dash" title="Not present in this version">—</span>
					{/if}
				</div>
			{/each}
		</div>
	{/each}
</div>

<style>
	.dual { max-width: 74rem; }
	.head, .row { display: grid; grid-template-columns: 3rem minmax(0, 1fr) minmax(0, 1fr); gap: 0 2rem; align-items: stretch; }
	.head .col { display: flex; align-items: baseline; gap: 0.6rem; padding-bottom: 0.7rem; border-bottom: 2px solid var(--ink); }
	.head .code { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.1em; color: var(--ink); }
	.head .name { font-size: 0.78rem; color: var(--muted); }
	.head .name[lang='ta'] { font-family: var(--tamil); }
	.heading { grid-column: 2 / -1; font-family: var(--sans); font-size: 1.06rem; font-weight: 600; color: var(--amber); margin: 1.4em 0 0.2em calc(3rem + 2rem); }
	.heading[lang='ta'] { font-family: var(--tamil); }
	.row { padding: 1.05rem 0; border-bottom: 1px solid var(--line); }
	.row.selected { background: var(--hl); box-shadow: 0 0 0 0.6rem var(--hl); border-radius: 2px; }
	.gn { display: flex; align-items: flex-start; justify-content: flex-end; border: 0; background: none; padding: 0.15rem 0; color: var(--muted); font-family: var(--sans); font-size: 0.9rem; font-weight: 700; cursor: pointer; line-height: 1.6; border-radius: 4px; }
	.gn:hover { color: var(--accent); }
	.row.selected .gn { color: var(--amber); }
	.gn .word { display: none; }
	/* verse numbers live in the gutter here */
	.cell :global(.vn) { display: none; }
	.cell[lang='ta'] { font-family: var(--tamil); font-size: 1.25rem; line-height: 1.85; text-wrap: pretty; }
	.cell[lang='en'] { font-family: var(--en); font-size: 1.12rem; line-height: 1.8; color: var(--ink-en); text-wrap: pretty; }
	.dash { color: var(--muted); }
	@media (max-width: 720px) {
		.head { display: none; }
		.heading { margin-left: 0; }
		.row { display: block; margin: 0 0 0.9rem; padding: 0; border: var(--bw) solid var(--line); border-radius: var(--r-xl); background: var(--surface); overflow: hidden; }
		.row.selected { background: var(--surface); box-shadow: none; border-color: var(--accent); }
		.gn { width: 100%; justify-content: flex-start; align-items: center; gap: 0.6rem; padding: 0.6rem 1rem; background: var(--surface-2); border-bottom: var(--bw) solid var(--line); border-radius: 0; }
		.gn .badge { width: 26px; height: 26px; border-radius: 999px; background: var(--accent); color: var(--on-accent); font-size: 0.78rem; display: inline-flex; align-items: center; justify-content: center; }
		.gn .word { display: inline; font-size: 0.72rem; }
		.gn .word:lang(ta) { font-family: var(--tamil); }
		.cell { padding: 0.9rem 1rem; }
		.cell + .cell { border-top: 1px dashed var(--line-2); }
		.cell[lang='ta'] { font-size: 1.22rem; line-height: 1.8; }
		.cell[lang='en'] { font-size: 1.06rem; line-height: 1.7; color: var(--ink-2); }
	}
</style>

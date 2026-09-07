<script lang="ts">
	// Two versions aligned verse by verse (R-9.1, R-9.2, R-9.4). Rows follow the
	// primary version's verse order; a verse missing from one side shows a dash.
	// On narrow screens each row stacks A above B, which is the interleaved form.
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

	type Row = { id: string; heading?: string; cells: (Segment[] | null)[] };

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
		return order.map<Row>((id) => ({
			id,
			heading: perVersion[0].headings.get(id),
			cells: perVersion.map((pv) => pv.map.get(id) ?? null)
		}));
	});
</script>

<div class="dual">
	<div class="head" aria-hidden="true">
		{#each versions as v (v.code)}<span>{v.short}</span>{/each}
	</div>
	{#each rows as row (row.id)}
		{#if row.heading}
			<h3 class="heading" lang={versions[0].lang}>{row.heading}</h3>
		{/if}
		<div class="row" data-verse={row.id}>
			{#each row.cells as cell, i (versions[i].code)}
				<div class="cell chapter" lang={versions[i].lang} class:missing={!cell}>
					{#if cell}
						{#each cell as seg, j (j)}
							<Verse {seg} lang={versions[i].lang} versionPath={versions[i].code.toLowerCase()} selected={selected.has(row.id)} onselect={i === 0 ? onselect : undefined} />
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
	.dual { max-width: 60rem; }
	.head { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.5rem; }
	.row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; padding: 0.35rem 0; border-top: 1px solid var(--line); }
	.row:hover { background: var(--surface); }
	.heading { font-family: var(--sans); font-size: 1rem; font-weight: 600; margin: 1.4em 0 0.4em; }
	.heading[lang='ta'] { font-family: var(--tamil); }
	.cell[lang='ta'] { font-family: var(--tamil); font-size: 1.02rem; line-height: 1.85; }
	.cell[lang='en'] { font-family: var(--serif); line-height: 1.65; }
	.dash { color: var(--muted); }
	@media (max-width: 720px) {
		.head { display: none; }
		.row { grid-template-columns: 1fr; gap: 0.4rem; }
		.cell + .cell { padding-left: 0.75rem; border-left: 2px solid var(--line); }
	}
</style>

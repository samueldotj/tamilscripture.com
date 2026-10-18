<script lang="ts">
	// The person page's family tree: ancestors row by row above the person, the
	// person with spouses and siblings, and below them each child as a branch
	// carrying the child's own children. Every name links to that person's page.
	import type { Family, Node } from './genealogy';

	let { family, self, gender, lang }: { family: Family; self: Node; gender: string; lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');

	const UP: [string, string][] = [
		['பெற்றோர்', 'Parents'],
		['தாத்தா, பாட்டி', 'Grandparents'],
		['கொள்ளுத் தாத்தா, பாட்டி', 'Great-grandparents'],
		['எள்ளுத் தாத்தா, பாட்டி', '2× great-grandparents']
	];
	/** Farthest generation first, as the tree is drawn top down. */
	const rows = $derived(family.ancestors.map((people, i) => ({ people, label: UP[i] ?? UP[UP.length - 1] })).reverse());
	const GRAND = 5;
	const name = (n: Node) => (ta && n.name_ta ? n.name_ta : n.name_en);
	const langOf = (n: Node) => (ta && n.name_ta ? 'ta' : 'en');
	const tip = (n: Node) => (ta && n.brief_ta ? n.brief_ta : n.brief);
	/** "mother: Hagar" under a child of a man with several wives; "father: …" for a woman's. */
	const otherLabel = $derived(gender === 'female' ? (ta ? 'தந்தை' : 'father') : ta ? 'தாய்' : 'mother');
</script>

<section class="tree card" aria-labelledby="tree-h">
	<h2 id="tree-h" class="kicker"><span lang="ta">குடும்ப மரம்</span> · Family tree</h2>

	{#each rows as r, i (i)}
		<div class="gen">
			<span class="label" {lang}>{ta ? r.label[0] : r.label[1]}</span>
			<ul class="row">
				{#each r.people as n (n.id)}
					<li><a class="node" href="/person/{n.id}" lang={langOf(n)} title={tip(n)}>{name(n)}</a></li>
				{/each}
			</ul>
		</div>
		<span class="stem" aria-hidden="true"></span>
	{/each}

	<div class="gen">
		<!-- The person stays on the tree's centre line: siblings to the left, spouses to the right. -->
		<div class="self-row">
			<ul class="sibs" aria-label={ta ? 'உடன்பிறந்தோர்' : 'Siblings'}>
				{#each family.siblings as n (n.id)}
					<li><a class="node sib" href="/person/{n.id}" lang={langOf(n)} title={tip(n)}>{name(n)}</a></li>
				{/each}
			</ul>
			<span class="node self" lang={langOf(self)} aria-current="page">{name(self)}</span>
			<ul class="partners" aria-label={ta ? 'துணை' : 'Spouses'}>
				{#each family.partners as n (n.id)}
					<li><span class="tie" aria-hidden="true">═</span><a class="node" href="/person/{n.id}" lang={langOf(n)} title={tip(n)}>{name(n)}</a></li>
				{/each}
			</ul>
		</div>
		{#if family.siblings.length || family.partners.length}
			<p class="legend" {lang}>
				{#if family.siblings.length}<span class="key sib"></span>{ta ? 'உடன்பிறந்தோர்' : 'siblings'}{/if}
				{#if family.partners.length}<span class="key">═</span>{ta ? 'துணை' : 'spouse'}{/if}
			</p>
		{/if}
	</div>

	{#if family.children.length}
		<span class="stem" aria-hidden="true"></span>
		<div class="gen">
			<span class="label" {lang}>{ta ? 'பிள்ளைகள், பேரப்பிள்ளைகள்' : 'Children and grandchildren'}</span>
			<div class="scroll">
				<ul class="kids">
					{#each family.children as c (c.id)}
						<li class="kid">
							<span class="drop" aria-hidden="true"></span>
							<a class="node" href="/person/{c.id}" lang={langOf(c)} title={tip(c)}>{name(c)}</a>
							{#if c.other}<span class="other" {lang}>{otherLabel}: <span lang={langOf(c.other)}>{name(c.other)}</span></span>{/if}
							{#if c.children.length}
								<ul class="grand">
									{#each c.children.slice(0, GRAND) as g (g.id)}
										<li><a class="node small" href="/person/{g.id}" lang={langOf(g)} title={tip(g)}>{name(g)}</a></li>
									{/each}
									{#if c.children.length > GRAND}
										<li><a class="more" href="/person/{c.id}" {lang}>+{c.children.length - GRAND} {ta ? 'மேலும்' : 'more'}</a></li>
									{/if}
								</ul>
							{/if}
						</li>
					{/each}
				</ul>
			</div>
		</div>
	{/if}
</section>

<style>
	/* Connectors in a muted ink, strong enough to read on the card in both themes. */
	.tree { --tree-line: color-mix(in srgb, var(--muted) 60%, transparent); padding: 1.1rem 1.3rem 1.3rem; display: flex; flex-direction: column; align-items: center; }
	.tree h2 { margin: 0 0 1rem; align-self: flex-start; }
	.tree h2 [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.gen { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; width: 100%; min-width: 0; }
	.label { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
	.label[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; font-size: 0.8rem; }
	ul { list-style: none; margin: 0; padding: 0; }
	.row { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 0.45rem; }
	.stem { display: block; width: var(--bw); height: 1.2rem; background: var(--tree-line); flex: none; }
	.node { display: inline-flex; align-items: center; min-height: 40px; padding: 0 0.85rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface-2); color: var(--ink); font-size: 0.9rem; text-decoration: none; white-space: nowrap; }
	.node[lang='ta'] { font-family: var(--tamil); }
	a.node:hover { border-color: var(--accent); color: var(--ink); }
	.node.self { border-color: var(--accent); background: var(--accent-soft); font-weight: 600; font-size: 1rem; }
	.node.sib { border-style: dashed; border-color: var(--tree-line); background: transparent; color: var(--ink-2); }
	.node.small { min-height: 34px; font-size: 0.82rem; padding: 0 0.7rem; }
	.self-row { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 0.5rem; width: 100%; }
	.sibs, .partners { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }
	.sibs { justify-content: flex-end; }
	.partners li { display: inline-flex; align-items: center; gap: 0.3rem; }
	.tie { color: var(--muted); font-size: 0.9rem; }
	.legend { margin: 0.1rem 0 0; display: flex; gap: 1rem; align-items: center; font-size: 0.75rem; color: var(--muted); }
	.legend[lang='ta'] { font-family: var(--tamil); }
	.key { display: inline-block; margin-right: 0.35rem; color: var(--muted); }
	.key.sib { width: 1.1rem; height: 0.7rem; border: var(--bw) dashed var(--tree-line); border-radius: 999px; vertical-align: middle; }
	/* Children: a bar across the top of the branches, a drop to each child. */
	.scroll { width: 100%; overflow-x: auto; padding-bottom: 0.3rem; }
	.kids { display: flex; width: max-content; min-width: 100%; justify-content: center; }
	.kid { position: relative; display: flex; flex-direction: column; align-items: center; gap: 0.35rem; padding: 0 0.35rem; }
	.kid::before, .kid::after { content: ''; position: absolute; top: 0; width: 50%; border-top: var(--bw) solid var(--tree-line); }
	.kid::before { left: 0; }
	.kid::after { right: 0; }
	.kid:first-child::before, .kid:last-child::after { display: none; }
	.drop { width: var(--bw); height: 0.9rem; background: var(--tree-line); }
	.other { font-size: 0.72rem; color: var(--muted); white-space: nowrap; }
	.other[lang='ta'], .other [lang='ta'] { font-family: var(--tamil); }
	.grand { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; margin-top: 0.15rem; padding-top: 0.5rem; border-top: var(--bw) dotted var(--tree-line); }
	.more { font-size: 0.8rem; font-weight: 600; text-decoration: none; min-height: 34px; display: inline-flex; align-items: center; }
	.more[lang='ta'] { font-family: var(--tamil); }
	/* On a phone the person comes first, then spouses, then siblings, each centred. */
	@media (max-width: 640px) {
		.self-row { display: flex; flex-direction: column; }
		.sibs { order: 3; justify-content: center; }
		.partners { order: 2; justify-content: center; }
	}
</style>

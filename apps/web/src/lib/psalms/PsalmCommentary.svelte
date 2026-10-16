<script lang="ts">
	// Spurgeon on the open psalm, in the explorer's reading pane: The Treasury of David's
	// overview of the psalm, its exposition verse by verse, its Explanatory Notes and Quaint
	// Sayings (quotations from other writers) and its Hints to the Village Preacher, one tab
	// each. The notes and hints are folded by verse and drawn only when opened: Psalm 119
	// alone has 170,000 words of them.
	import { findBook, verseUrl } from '$lib/content/manifest';
	import { settings } from '$lib/settings/store.svelte';
	import CommentaryText from '$lib/commentary/CommentaryText.svelte';
	import CommentaryFoot from '$lib/commentary/CommentaryFoot.svelte';
	import { unitVerses, type CommentaryChapter, type CommentarySource, type CommentaryUnit } from '$lib/commentary/load';

	let { chapter, source, n, ta }: { chapter: CommentaryChapter; source: CommentarySource | null; n: number; ta: boolean } = $props();

	type Section = 'exposition' | 'notes' | 'hints';
	type Tab = 'overview' | Section;
	const TABS: { id: Tab; ta: string; en: string }[] = [
		{ id: 'overview', ta: 'முன்னுரை', en: 'Overview' },
		{ id: 'exposition', ta: 'விளக்கவுரை', en: 'Exposition' },
		{ id: 'notes', ta: 'குறிப்புகள்', en: 'Notes and sayings' },
		{ id: 'hints', ta: 'பிரசங்கக் குறிப்புகள்', en: 'Hints to preachers' }
	];
	let tab = $state<Tab>('overview');
	let opened = $state<Record<string, boolean>>({});
	let more = $state(false);

	const lang = $derived<'ta' | 'en'>(ta ? 'ta' : 'en');

	// The overview: the psalm's introduction up to its notes; Title and Division (under
	// their headings) only once opened in full.
	const intro = $derived(chapter.units.find((u) => u.kind === 'chapter') ?? null);
	const overview = $derived(intro?.paragraphs.filter((p) => p.section === 'overview') ?? []);
	const lead = $derived.by(() => {
		// From the first paragraph (Psalm 119 opens with its Title heading) to the next heading.
		const from = overview.slice(overview.findIndex((p) => !p.heading));
		const k = from.findIndex((p) => p.heading);
		return (k < 0 ? from : from.slice(0, k)).slice(0, 2);
	});
	const overviewUnit = $derived<CommentaryUnit | null>(intro && overview.length ? { ...intro, paragraphs: more ? overview : lead } : null);

	const book = findBook('PSA')!;
	/** The verse page of a group's verses, in the reader's version; the site-wide hover preview shows the verse. */
	function href(u: CommentaryUnit): string | null {
		const [a, b] = unitVerses(u);
		return a ? verseUrl(settings.value.version, book, n, b > a ? `${a}-${b}` : `${a}`) : null;
	}

	function label(u: CommentaryUnit): string {
		const [a, b] = unitVerses(u);
		if (!a) return ta ? 'முழுச் சங்கீதம்' : 'The whole psalm';
		if (b > a) return ta ? `வசனங்கள் ${a}–${b}` : `Verses ${a}–${b}`;
		return ta ? `வசனம் ${a}` : `Verse ${a}`;
	}

	/** Each unit's paragraphs of one section, without the section's own heading. */
	function groups(section: Section) {
		return chapter.units.flatMap((u) => {
			const [a, b] = unitVerses(u);
			const paragraphs = u.paragraphs
				.filter((p) => p.section === section && !p.heading)
				// The group's heading names the verse, so the paragraph need not, unless the
				// group covers several and the paragraph is on one of them.
				.map((p) => (section === 'exposition' || a === b ? { ...p, verse: undefined } : p));
			if (!paragraphs.length) return [];
			const count = section === 'notes' ? new Set(paragraphs.map((p) => p.quote ?? p.id)).size : paragraphs.length;
			return [{ id: u.id, label: label(u), href: href(u), count, unit: { ...u, paragraphs } }];
		});
	}

	const all = $derived({ exposition: groups('exposition'), notes: groups('notes'), hints: groups('hints') });
	const has = (t: Tab) => (t === 'overview' ? !!overviewUnit : all[t].length > 0);
	// A psalm without an overview opens on its exposition.
	const current = $derived<Tab>(has(tab) ? tab : (TABS.find((t) => has(t.id))?.id ?? 'exposition'));
	const shown = $derived(current === 'overview' ? [] : all[current]);
	/** The tab's paragraphs together, for the provenance strip's English-or-Tamil state. */
	const together = $derived<CommentaryUnit>(
		current === 'overview' && overviewUnit
			? overviewUnit
			: { id: `spurgeon/PSA.${n}`, range: `PSA.${n}`, kind: 'chapter', paragraphs: shown.flatMap((g) => g.unit.paragraphs) }
	);

	function countLabel(count: number): string {
		if (current === 'notes') return ta ? `${count} மேற்கோள்கள்` : `${count} ${count === 1 ? 'quotation' : 'quotations'}`;
		return ta ? `${count} குறிப்புகள்` : `${count} ${count === 1 ? 'hint' : 'hints'}`;
	}
</script>

<section class="spur" aria-labelledby="spur-title">
	<h3 id="spur-title" class="kicker"><span lang="ta">ஸ்பர்ஜன்</span> · C. H. Spurgeon, <cite>The Treasury of David</cite></h3>
	<div class="tabs" role="group" aria-label={ta ? `சங்கீதம் ${n} — விளக்கம்` : `Spurgeon on Psalm ${n}`}>
		{#each TABS as t (t.id)}
			{#if has(t.id)}
				<button type="button" aria-pressed={current === t.id} onclick={() => (tab = t.id)} lang={ta ? 'ta' : 'en'}>{ta ? t.ta : t.en}</button>
			{/if}
		{/each}
	</div>

	{#if current === 'overview' && overviewUnit}
		<div class="overview">
			<CommentaryText unit={overviewUnit} {lang} versionPath={settings.value.version} />
			{#if overview.length > lead.length}
				<button type="button" class="more" aria-expanded={more} onclick={() => (more = !more)}>
					{more ? (ta ? 'சுருக்கு' : 'Show less') : ta ? 'முழு முன்னுரை' : 'Read the whole overview'}
				</button>
			{/if}
		</div>
	{:else if current === 'exposition'}
		<div class="list">
			{#each shown as g (g.id)}
				<article>
					<h4 lang={ta ? 'ta' : 'en'}>{#if g.href}<a class="vref" href={g.href}>{g.label}</a>{:else}{g.label}{/if}</h4>
					<CommentaryText unit={g.unit} {lang} versionPath={settings.value.version} />
				</article>
			{/each}
		</div>
	{:else}
		<div class="list folded">
			{#each shown as g (g.id)}
				<details bind:open={opened[`${current}:${g.id}`]}>
					<summary>
						{#if g.href}
							<!-- A plain click still opens and closes the row; the link is for the hover preview and a new tab. -->
							<a class="vref" href={g.href} lang={ta ? 'ta' : 'en'} onclick={(e) => { if (!e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) { e.preventDefault(); opened[`${current}:${g.id}`] = !opened[`${current}:${g.id}`]; } }}>{g.label}</a>
						{:else}
							<span lang={ta ? 'ta' : 'en'}>{g.label}</span>
						{/if}<span class="count" lang={ta ? 'ta' : 'en'}>{countLabel(g.count)}</span></summary>
					{#if opened[`${current}:${g.id}`]}
						<div class="body"><CommentaryText unit={g.unit} {lang} versionPath={settings.value.version} /></div>
					{/if}
				</details>
			{/each}
		</div>
	{/if}

	{#if source}<CommentaryFoot {source} unit={together} {lang} />{/if}
</section>

<style>
	.spur { border-top: var(--bw) solid var(--line); padding: 1.5rem var(--pad) 1.7rem; display: flex; flex-direction: column; gap: 1rem; }
	.kicker { margin: 0; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--amber); }
	.kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; }
	.kicker cite { font-style: normal; }
	/* A segmented control on a sunken track. */
	.tabs { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px; border-radius: 12px; background: var(--surface-3); align-self: flex-start; max-width: 100%; box-sizing: border-box; }
	.tabs button { min-height: 40px; padding: 0.35rem 0.95rem; border: 0; border-radius: 9px; background: none; color: var(--ink-2); font: inherit; font-size: 0.88rem; font-weight: 600; cursor: pointer; }
	.tabs button[lang='ta'] { font-family: var(--tamil); }
	.tabs button:hover { color: var(--ink); }
	.tabs button[aria-pressed='true'] { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12); }
	.overview { max-width: 44rem; font-size: 1.04rem; }
	.more { margin-top: 0.7rem; padding: 0.3rem 0; border: 0; background: none; color: var(--accent); font: inherit; font-size: 0.92rem; font-weight: 600; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
	.list { display: grid; gap: 1.4rem; max-width: 46rem; }
	.list.folded { gap: 0.5rem; }
	h4 { margin: 0 0 0.5rem; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--accent); }
	h4[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.92rem; }
	details { border: var(--bw) solid var(--line); border-radius: 12px; background: var(--surface); }
	summary { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; min-height: 44px; padding: 0.65rem 0.9rem; cursor: pointer; font-weight: 600; font-size: 0.95rem; list-style-position: inside; }
	summary [lang='ta'] { font-family: var(--tamil); }
	summary:hover { color: var(--accent); }
	.vref { color: inherit; text-decoration: underline dotted; text-decoration-color: var(--line-2); text-underline-offset: 0.25em; }
	.vref:hover { color: var(--accent); text-decoration-color: currentColor; }
	.count { font-size: 0.8rem; font-weight: 500; color: var(--muted); white-space: nowrap; }
	details[open] summary { border-bottom: var(--bw) solid var(--line); }
	.body { padding: 0.9rem 0.9rem 1rem; }
</style>

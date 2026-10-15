<script lang="ts">
	// The open psalm in the Psalms explorer, its reading pane (design: Psalms Explorer
	// Redesign, Oct 2026): the psalms before and after, the number and titles, theme,
	// genres, author and verse count, the key verse in the reader's Tamil and English
	// versions, summaries, Read / Sing / Share, Spurgeon's overview, exposition, notes and
	// hints (PsalmCommentary), more psalms of the theme, and the psalm to sing from the
	// 1650 Scottish Psalter (SingPsalm).
	import { onMount } from 'svelte';
	import { defaultFor, findBook, findVersion, chapterUrl, verseUrl } from '$lib/content/manifest';
	import { chapterCached, lastVerse, versesText } from '$lib/content/verses';
	import { settings } from '$lib/settings/store.svelte';
	import { loadCommentaryChapter, loadCommentaryIndex, type CommentaryChapter, type CommentarySource } from '$lib/commentary/load';
	import { loadPsalmCard } from './load';
	import type { Psalm, PsalmCard, PsalmsIndex } from './types';

	let { index, psalm, prev, next, onpick, ta }: { index: PsalmsIndex; psalm: Psalm; prev: number; next: number; onpick: (n: number) => void; ta: boolean } = $props();

	const book = findBook('PSA')!;
	const theme = $derived(index.themes.find((t) => t.id === psalm.theme)!);
	const themeOf = $derived(new Map(index.themes.map((t) => [t.id, t])));
	const genres = $derived(psalm.genres.map((id) => index.genres.find((g) => g.id === id)!));
	const authorName = (id: string) => index.authors.find((a) => a.id === id)!;
	const [kc, kv] = $derived(psalm.key.split(':'));
	const [ka, kb] = $derived(kv.split('-').map(Number));

	// The reader's own version, and the other language's default beside it.
	const reader = $derived(findVersion(settings.value.version) ?? defaultFor('ta')!);
	const taV = $derived(reader.lang === 'ta' ? reader : defaultFor('ta')!);
	const enV = $derived(reader.lang === 'en' ? reader : defaultFor('en')!);

	let card = $state<PsalmCard | null>(null);
	let verse = $state<{ ta: string; en: string } | null>(null);
	let verseCount = $state(0);
	// Spurgeon's chapter on the commentary CDN, fetched after paint like the reader's aids.
	let spurgeon = $state<CommentaryChapter | null>(null);
	let source = $state<CommentarySource | null>(null);
	let failed = $state(false);

	onMount(() => {
		loadPsalmCard(fetch, psalm.n).then((c) => (card = c)).catch(() => {});
		Promise.all([taV, enV].map((v) => chapterCached(fetch, v.code, 'PSA', Number(kc))))
			.then(([t, e]) => {
				verse = { ta: versesText(t, ka, kb ?? ka), en: versesText(e, ka, kb ?? ka) };
				verseCount = lastVerse(t);
			})
			.catch(() => {});
		loadCommentaryIndex(fetch).then((i) => (source = i.sources.find((s) => s.id === 'spurgeon') ?? null)).catch(() => {});
		loadCommentaryChapter(fetch, 'spurgeon', 'PSA', psalm.n)
			.then((c) => (c ? (spurgeon = c) : (failed = true)))
			.catch(() => (failed = true));
	});

	const titleTa = $derived(psalm.titleTa ?? `${theme.ta} சங்கீதம்`);
	const titleEn = $derived(psalm.titleEn ?? `A psalm of ${theme.en.toLowerCase()}`);
	const author = $derived.by(() => {
		const names = psalm.authors.map(authorName);
		if (names.length) return `${names.map((a) => a.ta).join(', ')} · ${names.map((a) => a.en).join(', ')}`;
		const nt = card?.nt;
		if (nt) {
			const a = nt.authors.map(authorName);
			return `${a.map((x) => x.ta).join(', ')} · ${a.map((x) => x.en).join(', ')} (${nt.ref})`;
		}
		return 'அநாமதேய · Anonymous';
	});
	const related = $derived(index.psalms.filter((r) => r[1] === psalm.theme && r[0] !== psalm.n).slice(0, 8).map((r) => r[0]));
	const keyLabel = $derived(psalm.key.replace('-', '–'));
	const verses = $derived(kb ? `${ka}-${kb}` : `${ka}`);
	const singable = $derived(!!card?.metrical?.length);
	const word = (t: string, e: string) => (ta ? t : e);
</script>

{#snippet step(n: number, back: boolean)}
	<button type="button" class="step" onclick={() => onpick(n)} aria-label="{word('சங்கீதம்', 'Psalm')} {n}">
		{#if back}<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>{/if}
		<span lang={ta ? 'ta' : 'en'}>{word('சங்கீதம்', 'Psalm')} {n}</span>
		{#if !back}<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>{/if}
	</button>
{/snippet}

<section class="card" aria-labelledby="psalm-title" style="--tc: {theme.color}">
	<div class="main">
		<div class="steps">
			{@render step(prev, true)}
			{@render step(next, false)}
		</div>

		<div class="head">
			<span class="num">{psalm.n}</span>
			<div class="titles">
				<span class="kicker">Psalm · <span lang="ta">சங்கீதம்</span></span>
				<h2 id="psalm-title" lang="ta">{titleTa}</h2>
				<p>{titleEn}</p>
			</div>
		</div>

		<div class="tags">
			<span class="tag theme"><i></i><span lang="ta">{theme.ta}</span> <span class="en">{theme.en}</span></span>
			{#each genres as g (g.id)}<span class="tag" lang={ta ? 'ta' : 'en'}>{ta ? g.ta : g.en}</span>{/each}
			{#each card?.tags ?? [] as t (t)}<span class="tag">{t}</span>{/each}
			<span class="tag author" lang="ta">{author}</span>
			{#if verseCount}<span class="tag plain" lang={ta ? 'ta' : 'en'}>{verseCount} {word('வசனங்கள்', 'verses')}</span>{/if}
		</div>

		<figure class="key">
			<span class="kicker amber">{word('முக்கிய வசனம்', 'Key verse')} · {keyLabel}</span>
			{#if verse}
				<blockquote lang="ta">{verse.ta}</blockquote>
				<figcaption lang="en">{verse.en}</figcaption>
			{:else}
				<p class="muted" aria-busy="true">…</p>
			{/if}
		</figure>

		{#if card?.summary_ta || card?.summary_en}
			<div class="sums">
				{#if card.summary_ta}<p class="sum-ta" lang="ta">{card.summary_ta}</p>{/if}
				{#if card.summary_en}<p class="sum-en">{card.summary_en}</p>{/if}
			</div>
		{/if}

		<div class="actions">
			<a class="btn primary" href={chapterUrl(settings.value.version, book, psalm.n)}><span lang="ta">முழு சங்கீதம்</span> · Read</a>
			{#if singable}
				<a class="btn" href="#sing">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></svg>
					<span lang="ta">பாடுக</span> <span class="en">Sing</span>
				</a>
			{/if}
			<a class="btn" href={verseUrl(settings.value.version, book, Number(kc), verses)}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7" /><path d="M16 6l-4-4-4 4" /><path d="M12 2v13" /></svg>
				<span lang="ta">பகிர்</span> <span class="en">Share</span>
			</a>
		</div>
	</div>

	{#if spurgeon}
		{#await import('./PsalmCommentary.svelte') then { default: PsalmCommentary }}
			<PsalmCommentary chapter={spurgeon} {source} n={psalm.n} {ta} />
		{/await}
	{:else}
		<p class="spur-state muted" aria-busy={!failed}>{failed ? word('விளக்கத்தை ஏற்ற முடியவில்லை.', 'Could not load the commentary.') : '…'}</p>
	{/if}

	{#if related.length}
		<div class="related">
			<span class="kicker">{ta ? `${theme.ta} — மேலும்` : `More on ${theme.en}`}</span>
			<div class="nums">
				{#each related as n (n)}<button type="button" style="--tc: {themeOf.get(psalm.theme)?.color}" aria-label="{word('சங்கீதம்', 'Psalm')} {n}" onclick={() => onpick(n)}>{n}</button>{/each}
			</div>
		</div>
	{/if}

	{#if singable && card}
		<div id="sing" class="sing-anchor">
			{#await import('./SingPsalm.svelte') then { default: SingPsalm }}
				<SingPsalm {card} {ta} />
			{/await}
		</div>
	{/if}
</section>

<style>
	/* One reading column: the psalm, then Spurgeon, more of the theme and the psalter below. */
	.card { --pad: 2.5rem; --tcx: var(--tc); display: flex; flex-direction: column; background: var(--surface); border: var(--bw) solid var(--line); border-radius: 20px; overflow: hidden; }
	@media (prefers-color-scheme: dark) { :global(:root:not([data-theme='light'])) .card { --tcx: color-mix(in oklab, var(--tc) 70%, white); } }
	:global(:root[data-theme='dark']) .card { --tcx: color-mix(in oklab, var(--tc) 70%, white); }
	.main { padding: 1.6rem var(--pad) 2rem; display: flex; flex-direction: column; gap: 1.4rem; }

	.steps { display: flex; justify-content: space-between; gap: 0.75rem; }
	.step { display: inline-flex; align-items: center; gap: 0.35rem; min-height: 40px; padding: 0 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 10px; background: none; color: var(--ink-2); font: inherit; font-size: 0.88rem; cursor: pointer; font-variant-numeric: tabular-nums; }
	.step [lang='ta'] { font-family: var(--tamil); }
	.step:hover { border-color: var(--accent); color: var(--ink); }

	.kicker { display: block; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.5rem; font-variant-numeric: tabular-nums; }
	.kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; }
	.kicker.amber { color: var(--amber); }
	.related .kicker { font-family: var(--tamil), var(--sans); }

	.head { display: flex; align-items: flex-end; gap: 0.6rem 1.75rem; flex-wrap: wrap; }
	.num { font-size: 7.5rem; line-height: 0.82; font-weight: 600; color: var(--accent); font-variant-numeric: lining-nums tabular-nums; letter-spacing: -0.04em; }
	.titles { flex: 1 1 16rem; min-width: 0; padding-bottom: 0.3rem; }
	.titles .kicker { margin-bottom: 0.3rem; }
	h2 { font-family: var(--tamil); font-weight: 600; font-size: 1.85rem; line-height: 1.25; margin: 0; text-wrap: balance; }
	.titles p { font-size: 1.12rem; color: var(--ink-2); margin: 0.2rem 0 0; line-height: 1.4; }

	.tags { display: flex; flex-wrap: wrap; gap: 0.45rem; }
	.tag { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 999px; font-size: 0.84rem; font-weight: 600; color: var(--ink-2); }
	.tag[lang='ta'], .tag [lang='ta'] { font-family: var(--tamil); }
	.tag .en { font-weight: 500; color: var(--muted); }
	.tag.theme { border-color: var(--tcx); color: var(--ink); }
	.tag.theme i { width: 9px; height: 9px; border-radius: 999px; background: var(--tcx); }
	.tag.author { border-color: transparent; background: var(--surface-2); font-family: var(--tamil), var(--sans); }
	.tag.plain { border-color: transparent; font-weight: 500; color: var(--muted); padding-inline: 0.3rem; }

	figure { margin: 0; }
	.key { padding: 1.3rem 1.5rem; border-radius: 14px; background: var(--bg); }
	.key .kicker { margin-bottom: 0.6rem; }
	blockquote { font-family: var(--tamil); font-size: 1.35rem; font-weight: 500; line-height: 1.7; margin: 0; }
	figcaption { font-size: 1.02rem; line-height: 1.6; margin-top: 0.5rem; color: var(--ink-2); font-style: italic; }

	.sums { display: flex; flex-direction: column; gap: 0.6rem; max-width: 44rem; }
	.sum-ta { font-family: var(--tamil); font-size: 1.05rem; line-height: 1.8; margin: 0; }
	.sum-en { font-size: 0.98rem; line-height: 1.65; margin: 0; color: var(--ink-en); }

	.actions { display: flex; gap: 0.6rem; flex-wrap: wrap; }
	.btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.45rem; min-height: 46px; padding: 0.5rem 1.1rem; border: var(--bw) solid var(--line-2); border-radius: 11px; background: none; color: var(--ink); font-weight: 600; font-size: 0.95rem; text-decoration: none; white-space: nowrap; }
	.btn:hover { border-color: var(--accent); }
	.btn .en { color: var(--ink-2); }
	.btn.primary { border-color: var(--accent); background: var(--accent); color: var(--on-accent); font-weight: 700; }
	.btn.primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
	.btn [lang='ta'] { font-family: var(--tamil); }

	.spur-state { margin: 0; padding: 1.4rem var(--pad); border-top: var(--bw) solid var(--line); }
	.related { padding: 1.4rem var(--pad) 1.6rem; border-top: var(--bw) solid var(--line); }
	.nums { display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.nums button { --tcx: var(--tc); width: 46px; height: 46px; padding: 0; border: 0; border-bottom: 3px solid var(--tcx); border-radius: 8px; background: color-mix(in srgb, var(--tcx) 14%, var(--surface)); color: var(--ink); font: inherit; font-weight: 600; font-size: 0.95rem; cursor: pointer; font-variant-numeric: tabular-nums; }
	@media (prefers-color-scheme: dark) { :global(:root:not([data-theme='light'])) .nums button { --tcx: color-mix(in oklab, var(--tc) 70%, white); } }
	:global(:root[data-theme='dark']) .nums button { --tcx: color-mix(in oklab, var(--tc) 70%, white); }
	.nums button:hover { outline: 2px solid var(--accent); outline-offset: 1px; }
	.sing-anchor { scroll-margin-top: calc(var(--header-h) + 1rem); }
	.muted { color: var(--muted); }

	@media (max-width: 52rem) {
		.card { --pad: 1.1rem; border-radius: 16px; }
		.main { padding-top: 1.2rem; gap: 1.1rem; }
		.steps { display: none; }
		.num { font-size: 5.2rem; }
		h2 { font-size: 1.45rem; }
		.key { padding: 1rem 1.1rem; }
		blockquote { font-size: 1.15rem; }
		.actions .btn { flex: 1 1 auto; }
	}
</style>

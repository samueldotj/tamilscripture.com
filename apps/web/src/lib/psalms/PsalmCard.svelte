<script lang="ts">
	// The open psalm in the Psalms explorer (design: Psalms Explorer v2, the card):
	// number and titles, theme, genres and author, summaries, the key verse in the
	// reader's Tamil and English versions, more psalms of the theme, Read and Share, and
	// below them the psalm to sing from the 1650 Scottish Psalter (SingPsalm).
	import { onMount } from 'svelte';
	import { defaultFor, findBook, findVersion, chapterUrl, verseUrl } from '$lib/content/manifest';
	import { chapterCached, versesText } from '$lib/content/verses';
	import { settings } from '$lib/settings/store.svelte';
	import { loadPsalmCard } from './load';
	import type { Psalm, PsalmCard, PsalmsIndex } from './types';

	let { index, psalm, onpick, ta }: { index: PsalmsIndex; psalm: Psalm; onpick: (n: number) => void; ta: boolean } = $props();

	const book = findBook('PSA')!;
	const theme = $derived(index.themes.find((t) => t.id === psalm.theme)!);
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
	let failed = $state(false);

	onMount(() => {
		loadPsalmCard(fetch, psalm.n).then((c) => (card = c)).catch(() => (failed = true));
		Promise.all([taV, enV].map((v) => chapterCached(fetch, v.code, 'PSA', Number(kc)).then((ch) => versesText(ch, ka, kb ?? ka))))
			.then(([t, e]) => (verse = { ta: t, en: e }))
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
</script>

<section class="card" aria-labelledby="psalm-title">
	<div class="left">
		<span class="kicker">Psalm · <span lang="ta">சங்கீதம்</span></span>
		<div class="head">
			<span class="num">{psalm.n}</span>
			<div class="titles">
				<h2 id="psalm-title" lang="ta">{titleTa}</h2>
				<p>{titleEn}</p>
			</div>
		</div>
		<div class="tags">
			<span class="tag theme" style="--tc: {theme.color}"><i></i>{ta ? theme.ta : theme.en}</span>
			{#each genres as g (g.id)}<span class="tag" lang={ta ? 'ta' : 'en'}>{ta ? g.ta : g.en}</span>{/each}
			{#each card?.tags ?? [] as t (t)}<span class="tag">{t}</span>{/each}
			<span class="tag author" lang="ta">{author}</span>
		</div>
		{#if card?.summary_ta}<p class="sum-ta" lang="ta">{card.summary_ta}</p>{/if}
		{#if card?.summary_en}<p class="sum-en">{card.summary_en}</p>{/if}
		{#if card && !card.summary_en && !card.summary_ta}
			<p class="sum-en muted">{ta ? 'சுருக்கம் விரைவில் சேர்க்கப்படும்.' : 'A short summary will be added here.'}</p>
		{/if}
	</div>
	<div class="right">
		<figure>
			<span class="kicker amber">{ta ? 'முக்கிய வசனம்' : 'Key verse'} · {keyLabel}</span>
			{#if verse}
				<blockquote lang="ta">{verse.ta}</blockquote>
				<figcaption>{verse.en}</figcaption>
			{:else if failed}
				<p class="muted">{ta ? 'வசனத்தை ஏற்ற முடியவில்லை.' : 'Could not load the verse.'}</p>
			{:else}
				<p class="muted" aria-busy="true">…</p>
			{/if}
		</figure>
		{#if related.length}
			<div>
				<span class="kicker">{ta ? `${theme.ta} — மேலும்` : `More on ${theme.en}`}</span>
				<div class="related">
					{#each related as n (n)}<button type="button" onclick={() => onpick(n)}>{n}</button>{/each}
				</div>
			</div>
		{/if}
		<div class="actions">
			<a class="btn primary" href={chapterUrl(settings.value.version, book, psalm.n)}><span lang="ta">முழு சங்கீதம்</span> · Read</a>
			<a class="btn" href={verseUrl(settings.value.version, book, Number(kc), verses)}>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7" /><path d="M16 6l-4-4-4 4" /><path d="M12 2v13" /></svg>
				{ta ? 'பகிர்' : 'Share'}
			</a>
		</div>
	</div>
	{#if card?.metrical?.length}
		{#await import('./SingPsalm.svelte') then { default: SingPsalm }}
			<SingPsalm {card} {ta} />
		{/await}
	{/if}
</section>

<style>
	.card { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); background: var(--surface); border: var(--bw) solid var(--line); border-radius: var(--r-xl); overflow: hidden; }
	.left { padding: 1.5rem 1.5rem 1.6rem; }
	.right { background: var(--surface-2); padding: 1.5rem; display: flex; flex-direction: column; gap: 1.2rem; border-left: var(--bw) solid var(--line); }
	.kicker { display: block; font-size: 0.76rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.6rem; font-variant-numeric: tabular-nums; }
	.kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; }
	.kicker.amber { color: var(--amber); margin-bottom: 0.5rem; }
	.head { display: flex; align-items: flex-start; gap: 1.1rem; flex-wrap: wrap; }
	.num { font-size: 3.6rem; line-height: 1; font-weight: 600; color: var(--accent); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
	.titles { flex: 1 1 14rem; min-width: 0; }
	h2 { font-family: var(--tamil); font-weight: 600; font-size: 1.5rem; line-height: 1.3; margin: 0; }
	.titles p { font-size: 1.05rem; color: var(--ink-2); margin: 0.15rem 0 0; line-height: 1.4; }
	.tags { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 1rem; }
	.tag { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.7rem; border: var(--bw) solid var(--line-2); border-radius: 999px; font-size: 0.8rem; font-weight: 600; color: var(--ink-2); }
	.tag[lang='ta'] { font-family: var(--tamil); }
	.tag.theme { border-color: var(--tc); color: var(--ink); }
	.tag.theme i { width: 8px; height: 8px; border-radius: 999px; background: var(--tc); }
	.tag.author { border-color: transparent; background: var(--surface-2); font-family: var(--tamil), var(--sans); }
	.sum-ta { font-family: var(--tamil); font-size: 1.05rem; line-height: 1.8; margin: 1.2rem 0 0; }
	.sum-en { font-size: 0.95rem; line-height: 1.65; margin: 0.6rem 0 0; color: var(--ink-en); }
	figure { margin: 0; }
	blockquote { font-family: var(--tamil); font-size: 1.3rem; line-height: 1.9; margin: 0; padding: 0.15rem 0.35rem; background: var(--hl); border-radius: 6px; box-decoration-break: clone; -webkit-box-decoration-break: clone; display: inline; }
	figcaption { font-size: 0.98rem; line-height: 1.6; margin-top: 0.8rem; color: var(--ink-en); }
	.related { display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.related button { display: inline-flex; align-items: center; justify-content: center; min-height: 36px; min-width: 44px; padding: 0.3rem 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 11px; background: var(--surface); color: var(--ink); font: inherit; font-weight: 600; font-size: 0.85rem; cursor: pointer; font-variant-numeric: tabular-nums; }
	.related button:hover { border-color: var(--accent); }
	.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: auto; }
	.btn { display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; min-height: 42px; padding: 0.5rem 0.95rem; border: var(--bw) solid var(--line-2); border-radius: 11px; background: var(--surface); color: var(--ink); font-weight: 600; font-size: 0.92rem; text-decoration: none; white-space: nowrap; }
	.btn:hover { border-color: var(--accent); }
	.btn.primary { border-color: var(--accent); background: var(--accent); color: var(--on-accent); }
	.btn.primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
	.btn [lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); }
	@media (max-width: 52rem) {
		.right { border-left: 0; border-top: var(--bw) solid var(--line); }
		.num { font-size: 2.8rem; }
	}
</style>

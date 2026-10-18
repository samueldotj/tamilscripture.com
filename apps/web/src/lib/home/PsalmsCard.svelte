<script lang="ts">
	// Psalms explorer sample: the 150 psalms coloured by theme (tap a theme to
	// pick them out, a number to choose one), and the chosen psalm's tune to sing along.
	import { loadPsalmCard, loadPsalmsIndex } from '$lib/psalms/load';
	import { EMPTY, toQuery } from '$lib/psalms/filter';
	import { psalmOf, type PsalmCard, type PsalmsIndex } from '$lib/psalms/types';
	import Card from './Card.svelte';

	let { lang }: { lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');

	let index = $state<PsalmsIndex | null>(null);
	let theme = $state<string | null>(null);
	let n = $state(23);
	let card = $state<PsalmCard | null>(null);

	const psalms = $derived(index ? index.psalms.map(psalmOf) : []);
	const colour = $derived(new Map(index?.themes.map((t) => [t.id, t]) ?? []));
	const sel = $derived(psalms.find((p) => p.n === n));
	const href = $derived(`/psalms?${toQuery(theme ? { ...EMPTY, themes: [theme] } : EMPTY, n)}`);

	function load() {
		loadPsalmsIndex(fetch).then((i) => (index = i)).catch(() => {});
		choose(23);
	}
	function choose(m: number) {
		n = m;
		loadPsalmCard(fetch, m).then((c) => { if (n === m) card = c; }).catch(() => (card = null));
	}

	const tune = $derived(card && card.n === n ? card.tunes[0] : undefined);
	const metrical = $derived(card && card.n === n ? card.metrical[0] : undefined);
	/** The first line of the metrical psalm from its syllables ("shep-" "herd," → "shepherd,"). */
	const line = $derived.by(() => {
		const syl = metrical?.lyrics?.[0]?.[0];
		if (!syl) return metrical?.stanzas[0]?.[0]?.replace(/^[\s¹²³⁴⁵⁶⁷⁸⁹⁰]+/, '') ?? '';
		return syl.reduce((s, x) => (s.endsWith('-') ? s.slice(0, -1) + x : s ? `${s} ${x}` : x), '');
	});
	// Two octaves, white keys then the black keys between them.
	const WHITES = 14;
	const BLACKS = [0, 1, 3, 4, 5, 7, 8, 10, 11, 12];
</script>

<Card ta="சங்கீதங்கள்" en="Psalms explorer" tag={ta ? '150 பாடல்கள்' : '150 songs'} href={href} cta={ta ? 'சங்கீதங்களை ஆராய' : 'Explore the psalms'} {lang} onvisible={load}>
	{#if index}
		<div class="themes" role="group" aria-label={ta ? 'கருப்பொருள்' : 'Theme'}>
			{#each index.themes as t (t.id)}
				<button type="button" class="chip" class:on={theme === t.id} aria-pressed={theme === t.id} onclick={() => (theme = theme === t.id ? null : t.id)} {lang}>
					<span class="sw" style:background={t.color} aria-hidden="true"></span>{ta ? t.ta : t.en}
				</button>
			{/each}
		</div>
		<div class="grid">
			{#each psalms as p (p.n)}
				<button type="button" class="cell" class:sel={p.n === n} class:dim={!!theme && p.theme !== theme}
					style:background={colour.get(p.theme)?.color}
					aria-label="{ta ? 'சங்கீதம்' : 'Psalm'} {p.n}" aria-pressed={p.n === n} onclick={() => choose(p.n)}>{p.n === n ? p.n : ''}</button>
			{/each}
		</div>
		{#if sel}
			<div class="chosen">
				<span class="num" style:background={colour.get(sel.theme)?.color}>{sel.n}</span>
				<div class="what">
					<div class="t" {lang}>{ta ? 'சங்கீதம்' : 'Psalm'} {sel.n} · <span class="th">{ta ? colour.get(sel.theme)?.ta : colour.get(sel.theme)?.en}</span></div>
					{#if (ta ? sel.titleTa : sel.titleEn) ?? sel.titleEn}<div class="sub" lang={ta && sel.titleTa ? 'ta' : 'en'}>{ta ? (sel.titleTa ?? sel.titleEn) : sel.titleEn}</div>{/if}
				</div>
			</div>
		{/if}
	{:else}
		<div class="ph" aria-hidden="true"></div>
	{/if}

	{#if tune && metrical}
		<div class="sing">
			<div class="sing-head">
				<a class="play" href="{href}#sing" aria-label={ta ? `சங்கீதம் ${n} பாடுங்கள்` : `Sing Psalm ${n}`}>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5l11 7-11 7z" /></svg>
				</a>
				<div class="tune">
					<p class="kicker"><span lang="ta">சேர்ந்து பாடுங்கள்</span> · Sing along</p>
					<div class="tn">{tune.name} <span>· {metrical.label} {metrical.meter} · Scottish Psalter 1650</span></div>
				</div>
			</div>
			<div class="keys" aria-hidden="true">
				{#each { length: WHITES } as _, i (i)}<span class="w" style:animation-delay="{(i * 0.7) % 4.9}s"></span>{/each}
				{#each BLACKS as b (b)}<span class="b" style:left="calc({((b + 1) * 100) / WHITES}% - 2.3%)"></span>{/each}
			</div>
			{#if line}<p class="line" lang="en">{line}</p>{/if}
		</div>
	{/if}
</Card>

<style>
	.themes { display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.chip { display: inline-flex; align-items: center; gap: 0.4rem; min-height: 36px; padding: 0 0.75rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font: 0.84rem var(--sans); cursor: pointer; }
	.chip[lang='ta'] { font-family: var(--tamil); }
	.chip.on { border-color: var(--ink); background: var(--surface-2); }
	.sw { width: 0.65rem; height: 0.65rem; border-radius: 3px; }
	.grid { display: grid; grid-template-columns: repeat(15, minmax(0, 1fr)); gap: 3px; }
	.cell { aspect-ratio: 1; border: 0; padding: 0; border-radius: 4px; cursor: pointer; color: #fff; font: 600 0.62rem var(--sans); transition: opacity 0.15s; }
	.cell.dim { opacity: 0.18; }
	.cell.sel { outline: 2px solid var(--ink); outline-offset: 1px; }
	.chosen { display: flex; gap: 0.9rem; align-items: center; padding: 0.8rem 1rem; border-radius: var(--r-l); background: var(--surface-2); }
	.num { flex: none; width: 2.8rem; height: 2.8rem; border-radius: 10px; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; }
	.what { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
	.t { font-weight: 600; }
	.t[lang='ta'], .sub[lang='ta'] { font-family: var(--tamil); }
	.th { font-weight: 400; color: var(--ink-2); }
	.sub { font-size: 0.88rem; color: var(--ink-2); }
	.ph { min-height: 16rem; border-radius: var(--r-l); background: var(--surface-2); }
	.sing { display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; border: var(--bw) solid var(--line); border-radius: var(--r-l); }
	.sing-head { display: flex; align-items: center; gap: 0.8rem; }
	.play { flex: none; width: 48px; height: 48px; border-radius: 50%; background: var(--accent); color: var(--on-accent); display: flex; align-items: center; justify-content: center; }
	.play:hover { background: var(--accent-hover); color: var(--on-accent); }
	.tune { min-width: 0; }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; }
	.tn { font-weight: 600; }
	.tn span { font-weight: 400; font-size: 0.82rem; color: var(--muted); }
	.keys { position: relative; height: 5rem; display: flex; gap: 2px; }
	/* A piano is ivory and black in either theme. */
	.w { flex: 1; border: var(--bw) solid var(--line-2); border-top: 0; border-radius: 0 0 6px 6px; background: #FBF7F0; animation: lit 4.9s infinite; }
	.b { position: absolute; top: 0; width: 4.6%; height: 62%; background: #2A241E; border-radius: 0 0 4px 4px; }
	@keyframes lit { 0%, 12% { background: var(--accent); } 14%, 100% { background: #FBF7F0; } }
	@media (prefers-reduced-motion: reduce) { .w { animation: none; } }
	.line { margin: 0; font-size: 0.95rem; color: var(--ink-2); font-style: italic; }
</style>

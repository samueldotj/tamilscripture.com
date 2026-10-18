<script lang="ts">
	// Root words sample: John 3:16 in Greek, word by word; tap one to see its
	// Strong's entry — meaning, how often it is used, and in which books.
	import { findBook } from '$lib/content/manifest';
	import { loadOriginal, loadStrongs, type StrongsEntry } from '$lib/entities/load';
	import Card from './Card.svelte';

	let { lang }: { lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');

	type Word = [string, string, string, string, string];
	let words = $state<Word[]>([]);
	let num = $state('G0025');
	let entry = $state<StrongsEntry | null>(null);
	/** Nouns, verbs, adjectives and adverbs open an entry; articles and particles stay plain. */
	const content = (w: Word) => /^(N|V|A|ADV)\b/.test(w[4]);

	function load() {
		loadOriginal(fetch, 'JHN', 3).then((c) => (words = c.verses['16'] ?? [])).catch(() => {});
		choose('G0025');
	}
	function choose(s: string) {
		num = s;
		loadStrongs(fetch, s).then((e) => { if (num === s) entry = e; }).catch(() => {});
	}
	const top = $derived(entry ? [...entry.books].sort((a, b) => b[1] - a[1]).slice(0, 5) : []);
	const max = $derived(top[0]?.[1] ?? 1);
	const bookName = (code: string) => { const b = findBook(code); return b ? (ta ? b.name_ta : b.name_en) : code; };
</script>

<Card ta="மூலச்சொற்கள்" en="Root words" tag={ta ? 'யோவான் 3:16 · கிரேக்கம்' : 'John 3:16 · Greek'} href="/strongs/{num}" cta={ta ? `${num} உள்ள எல்லா வசனங்களும்` : `Every verse with ${num}`} {lang} onvisible={load}>
	{#if words.length}
		<p class="greek" lang="grc">
			{#each words as w, i (i)}
				{#if content(w)}
					<button type="button" class:on={w[3] === num} aria-pressed={w[3] === num} onclick={() => choose(w[3])}><span class="g">{w[0]}</span><span class="gl" lang="en">{w[2]}</span></button>
				{:else}
					<span class="plain"><span class="g">{w[0]}</span><span class="gl" lang="en">{w[2]}</span></span>
				{/if}
			{/each}
		</p>
	{/if}
	{#if entry}
		<div class="entry">
			<p class="kicker"><span lang="ta">ஒத்த வசன அகராதி</span> · Concordance · {entry.s}</p>
			<div class="lemma"><span lang={entry.script === 'el' ? 'grc' : 'he'}>{entry.lemma}</span> <i>{entry.translit}</i></div>
			<div class="gloss">{#if entry.gloss_ta}<span lang="ta">{entry.gloss_ta}</span> · {/if}<span lang="en">{entry.gloss}</span></div>
			<div class="count" {lang}>{ta ? `${entry.count} முறை` : `${entry.count} times`}</div>
			<ul class="bars">
				{#each top as [code, n] (code)}
					<li><span class="bk" {lang}>{bookName(code)}</span><span class="bar"><span style:width="{(n / max) * 100}%"></span></span><span class="n">{n}</span></li>
				{/each}
			</ul>
		</div>
	{:else}
		<div class="ph" aria-hidden="true"></div>
	{/if}
</Card>

<style>
	.greek { margin: 0; display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.greek button, .plain { display: inline-flex; flex-direction: column; align-items: center; gap: 0.05rem; min-height: 3.4rem; padding: 0.35rem 0.6rem; border-radius: var(--r); box-sizing: border-box; }
	.greek button { border: var(--bw) solid var(--line); background: var(--surface); color: var(--ink); cursor: pointer; font: inherit; }
	.greek button:hover { border-color: var(--accent); }
	.greek button.on { border-color: var(--accent); background: var(--accent-soft); }
	.plain { color: var(--muted); }
	.g { font-size: 1.05rem; }
	.gl { font-size: 0.72rem; color: var(--muted); }
	.entry { display: flex; flex-direction: column; gap: 0.5rem; padding: 1rem 1.1rem; border-radius: var(--r-l); background: var(--surface-2); }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; }
	.lemma { font-size: 1.6rem; font-weight: 600; }
	.lemma i { font-size: 1rem; font-weight: 400; color: var(--ink-2); }
	.gloss [lang='ta'], .count[lang='ta'], .bk[lang='ta'] { font-family: var(--tamil); }
	.gloss [lang='ta'] { font-weight: 600; }
	.count { font-size: 0.88rem; color: var(--ink-2); }
	.bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.3rem; }
	.bars li { display: grid; grid-template-columns: 7.5rem 1fr 2rem; align-items: center; gap: 0.6rem; font-size: 0.85rem; }
	.bk { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.bar { height: 0.55rem; border-radius: 999px; background: var(--surface-3); overflow: hidden; }
	.bar span { display: block; height: 100%; background: var(--accent); border-radius: 999px; }
	.n { text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }
	.ph { min-height: 12rem; border-radius: var(--r-l); background: var(--surface-2); }
</style>

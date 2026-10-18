<script lang="ts">
	// Dictionary sample: the opening of Easton's "Bethlehem", in Tamil where the
	// draft exists, and the letters to browse the dictionary by.
	import { loadArticle } from '$lib/entities/load';
	import { sourceOf } from '$lib/entities/sources';
	import type { Article } from '$lib/entities/types';
	import RefText from '$lib/refs/RefText.svelte';
	import Card from './Card.svelte';

	let { lang, versionPath }: { lang: 'ta' | 'en'; versionPath: string } = $props();
	const ta = $derived(lang === 'ta');
	const ID = 'eastons/bethlehem';
	const TA_LETTERS = 'அ ஆ இ ஈ உ ஊ எ ஏ ஐ ஒ ஓ க ச ஞ த ந ப ம ய ர ல வ'.split(' ');
	const EN_LETTERS = 'A B C D E F G H I J K L M N O P Q R S T U V W Y Z'.split(' ');
	const letters = $derived(ta ? TA_LETTERS : EN_LETTERS);
	const here = $derived(ta ? 'ப' : 'B');

	let a = $state<Article | null>(null);
	const load = () => loadArticle(fetch, ID).then((x) => (a = x)).catch(() => {});
	const showTa = $derived(ta && !!a?.paragraphs.some((p) => p.ta));
	const paras = $derived((a?.paragraphs ?? []).slice(0, 2).map((p) => (showTa ? (p.ta ?? p.text) : p.text)));
</script>

<Card ta="அகராதி" en="Dictionary" href="/dictionary" cta={ta ? 'அகராதியைத் திற' : 'Open the dictionary'} {lang} onvisible={load}>
	<nav class="letters" aria-label={ta ? 'எழுத்து வாரியாக' : 'By letter'}>
		{#each letters as l (l)}
			<a href="/dictionary?l={encodeURIComponent(l)}{ta ? '' : '&lang=en'}" class:on={l === here} lang={ta ? 'ta' : 'en'}>{l}</a>
		{/each}
	</nav>
	{#if a}
		<a class="entry" href="/dictionary/{ID}">
			<span class="hw"><span lang="ta">{a.title_ta ?? a.title}</span> <span class="en">{a.title}</span></span>
			<span class="kicker">{sourceOf(a.source).name}</span>
		</a>
		<div class="text" lang={showTa ? 'ta' : 'en'}>
			{#each paras as p, i (i)}<p class:lead={i === 0}><RefText text={p} version={versionPath} /></p>{/each}
		</div>
	{:else}
		<div class="ph" aria-hidden="true"></div>
	{/if}
</Card>

<style>
	.letters { display: flex; flex-wrap: wrap; gap: 0.2rem; }
	.letters a { min-width: 2.1rem; min-height: 2.1rem; display: flex; align-items: center; justify-content: center; border-radius: var(--r-s); color: var(--ink-2); font-weight: 600; text-decoration: none; }
	.letters a[lang='ta'] { font-family: var(--tamil); }
	.letters a:hover { background: var(--surface-2); }
	.letters a.on { background: var(--accent); color: var(--on-accent); }
	.entry { display: flex; flex-direction: column; gap: 0.2rem; text-decoration: none; color: inherit; }
	.hw { font-size: 1.45rem; font-weight: 600; }
	.hw [lang='ta'] { font-family: var(--tamil); }
	.hw .en { font-size: 0.95rem; font-weight: 400; color: var(--ink-2); }
	.entry:hover .hw [lang='ta'] { color: var(--accent); }
	.kicker { margin: 0; }
	.text { display: flex; flex-direction: column; gap: 0.6rem; max-height: 12rem; overflow: hidden; -webkit-mask-image: linear-gradient(#000 70%, transparent); mask-image: linear-gradient(#000 70%, transparent); }
	.text[lang='ta'] { font-family: var(--tamil); }
	.text p { margin: 0; line-height: 1.75; color: var(--ink-en); }
	.text p.lead { font-weight: 600; color: var(--amber); }
	.ph { min-height: 12rem; border-radius: var(--r-l); background: var(--surface-2); }
</style>

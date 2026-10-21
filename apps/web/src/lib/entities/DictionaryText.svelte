<script lang="ts">
	// A dictionary article as the main text of a person or place page: in the
	// site language (Tamil, or the English original under EN), with a switch
	// between the dictionaries that have an entry of this name, one draft
	// badge and one correction control, as on the article page. Every entry is
	// in the page, so search engines read the articles this page is the home
	// of; an article about several people or places shows its opening here and
	// lives on its own page (seo.ts).
	import RefText from '$lib/refs/RefText.svelte';
	import SuggestControl from '$lib/community/SuggestControl.svelte';
	import Provenance from '$lib/community/Provenance.svelte';
	import { articleTarget } from '$lib/community/repo';
	import { sourceOf } from '$lib/entities/sources';
	import { excerpt, ownedBy } from '$lib/entities/seo';
	import type { Article } from '$lib/entities/types';

	let { articles, owner, chosen = false, lang }: { articles: Article[]; owner: string; chosen?: boolean; lang: 'ta' | 'en' } = $props();

	const ta = $derived(lang === 'ta');
	let shownId = $state<string | null>(null);
	const a = $derived(articles.find((x) => x.id === shownId) ?? articles[0]);
	const src = $derived(sourceOf(a.source));
	const hasTa = $derived(a.paragraphs.some((p) => p.ta));
	const corrections = $derived(a.paragraphs.filter((p) => p.ta_source === 'community' || p.ta_source === 'owner').length);
	const choices = $derived(
		a.paragraphs.map((p, i) => {
			const text = (p.ta ?? p.text).replace(/\s+/g, ' ');
			return { target: articleTarget(p.id), current: p.ta ?? '', source: p.text, label: `${i + 1}. ${text.length > 70 ? text.slice(0, 70) + '…' : text}` };
		})
	);
</script>

<section class="dict card">
	<div class="top">
		<h2 class="kicker"><span lang="ta">அகராதி</span> · Dictionary</h2>
		{#if articles.length > 1}
			<div class="pills" role="group" aria-label={ta ? 'அகராதி மூலம்' : 'Dictionary source'}>
				{#each articles as e (e.id)}
					<button type="button" class="pill" class:on={e.id === a.id} aria-pressed={e.id === a.id} onclick={() => (shownId = e.id)}>{sourceOf(e.source).short}</button>
				{/each}
			</div>
		{/if}
	</div>

	{#each articles as x (x.id)}
		{@const xTa = ta && x.paragraphs.some((p) => p.ta)}
		<div class="body" hidden={x.id !== a.id}>
			{#if ownedBy(x, owner, chosen)}
				{#each x.paragraphs as p (p.id)}
					{@const tamil = xTa && p.ta}
					{#if p.heading}
						<h3 lang={tamil ? 'ta' : 'en'}>{tamil ? p.ta : p.text}</h3>
					{:else}
						<p lang={tamil ? 'ta' : 'en'} class:ta={tamil}><RefText text={(tamil ? p.ta : p.text) ?? ''} /></p>
					{/if}
				{/each}
			{:else}
				<p lang={xTa ? 'ta' : 'en'} class:ta={xTa}>{excerpt(x, !xTa)}</p>
				<p class="more"><a href="/dictionary/{x.id}" lang={ta ? 'ta' : 'en'}>{ta ? 'முழுக் கட்டுரையை வாசிக்க →' : 'Read the full entry →'}</a></p>
			{/if}
		</div>
	{/each}

	<div class="foot">
		<div class="meta">
			<a class="name" href="/dictionary/{a.id}">{src.name}, {src.year}</a>
			<span class="state" lang={ta ? 'ta' : 'en'}>
				{#if hasTa}
					{ta ? 'தமிழாக்கம்' : 'Tamil translation'}
					{#if corrections}· <span class="ok">✓ {corrections} {ta ? 'சமூக திருத்தங்கள்' : corrections === 1 ? 'community correction' : 'community corrections'}</span>
					{:else}<Provenance kind="draft" lang={lang} />{/if}
				{:else}
					{ta ? 'தமிழாக்கம் இன்னும் இல்லை' : 'no Tamil translation yet'}
				{/if}
			</span>
		</div>
		{#key a.id}<div class="suggest-slot"><SuggestControl {choices} {lang} /></div>{/key}
	</div>
	<p class="attr">{a.attribution}</p>
</section>

<style>
	.dict { padding: 1.1rem 1.3rem; display: grid; gap: 0.8rem; }
	.top { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; flex-wrap: wrap; }
	.top .kicker { margin: 0; }
	.top .kicker [lang='ta'] { font-family: var(--tamil); }
	.pills { display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.pill { font: inherit; font-size: 0.82rem; font-weight: 600; min-height: 32px; padding: 0.15rem 0.75rem; border: var(--bw, 1px) solid var(--line-2); border-radius: 999px; background: none; color: var(--ink-2); cursor: pointer; }
	.pill:hover { border-color: var(--accent); color: var(--accent); }
	.pill.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.body { display: grid; gap: 0.9rem; }
	.body[hidden] { display: none; }
	.more { font-size: 0.88rem; font-weight: 600; }
	.more a { text-decoration: none; }
	.more [lang='ta'] { font-family: var(--tamil); }
	.body p { margin: 0; line-height: 1.75; font-size: 1.02rem; }
	.body p.ta { font-family: var(--tamil); font-size: 1.1rem; line-height: 1.9; }
	.body h3 { margin: 0.4rem 0 0; font-size: 1.05rem; font-weight: 700; }
	.body h3[lang='ta'] { font-family: var(--tamil); }
	.foot { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; flex-wrap: wrap; padding-top: 0.7rem; border-top: 1px solid var(--line); }
	.meta { display: grid; gap: 0.1rem; }
	.name { font-size: 0.84rem; font-weight: 600; color: inherit; text-decoration: none; }
	.name:hover { color: var(--accent); }
	.state { font-size: 0.78rem; color: var(--muted); }
	.state[lang='ta'] { font-family: var(--tamil); }
	.ok { color: var(--good); font-weight: 600; }
	.suggest-slot { flex: 1 1 auto; display: flex; justify-content: flex-end; min-width: 0; }
	.suggest-slot:has(:global(form)) { flex-basis: 100%; justify-content: flex-start; }
	.attr { margin: 0; font-size: 0.75rem; color: var(--muted); }
</style>

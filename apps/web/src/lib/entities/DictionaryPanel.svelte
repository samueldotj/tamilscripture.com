<script lang="ts">
	// Dictionary tab: articles for the entities named in the selected verse
	// (or the whole chapter when nothing is selected), opening paragraphs
	// loaded on demand.
	import type { ChapterMentions, Article } from '$lib/entities/types';
	import { loadArticle } from '$lib/entities/load';

	let {
		mentions,
		selected = new Set<string>(),
		lang,
		loading = false
	}: {
		mentions: ChapterMentions | null;
		selected?: Set<string>;
		lang: 'ta' | 'en';
		loading?: boolean;
	} = $props();

	const ta = $derived(lang === 'ta');
	type Item = { article: string; name: string; kind: 'place' | 'person' };
	const items = $derived.by((): Item[] => {
		if (!mentions) return [];
		const inSelection = new Set<string>();
		if (selected.size) {
			for (const v of mentions.verses) {
				if (!selected.has(v.verse)) continue;
				for (const id of v.places) inSelection.add(`place/${id}`);
				for (const id of v.people ?? []) inSelection.add(`person/${id}`);
			}
		}
		const seen = new Set<string>();
		const out: Item[] = [];
		const push = (kind: 'place' | 'person', id: string, article: string | null | undefined, name: string) => {
			if (!article || seen.has(article)) return;
			if (selected.size && !inSelection.has(`${kind}/${id}`)) return;
			seen.add(article);
			out.push({ article, name, kind });
		};
		for (const v of mentions.verses) {
			for (const id of v.places) push('place', id, mentions.places[id]?.article, mentions.places[id]?.name_en ?? id);
			for (const id of v.people ?? []) push('person', id, mentions.people?.[id]?.article, mentions.people?.[id]?.name_en ?? id);
		}
		return out;
	});
	const cache = new Map<string, Promise<Article>>();
	function article(id: string) {
		if (!cache.has(id)) cache.set(id, loadArticle(fetch, id));
		return cache.get(id)!;
	}
</script>

<div class="dict">
	{#if loading}
		<p class="hint">…</p>
	{:else if items.length === 0}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? (selected.size ? 'தேர்ந்த வசனத்தின் பெயர்களுக்கு அகராதிக் கட்டுரைகள் இல்லை.' : 'இந்த அதிகாரத்தின் பெயர்களுக்கு அகராதிக் கட்டுரைகள் இல்லை.') : (selected.size ? 'No dictionary articles for the names in the selected verse.' : 'No dictionary articles for the names in this chapter.')}</p>
	{:else}
		<h3 class="kicker"><span lang="ta">அகராதி</span> · Easton's Bible Dictionary <span class="n">{items.length}</span></h3>
		<ul class="list">
			{#each items.slice(0, 12) as it (it.article)}
				<li>
					<a class="title" href="/dictionary/{it.article}">{it.name}</a>
					{#await article(it.article)}
						<p class="snippet muted">…</p>
					{:then a}
						<p class="snippet" lang={a.paragraphs[0]?.ta ? 'ta' : 'en'}>{(a.paragraphs[0]?.ta ?? a.paragraphs[0]?.text ?? '').slice(0, 220)}{(a.paragraphs[0]?.ta ?? a.paragraphs[0]?.text ?? '').length > 220 ? '…' : ''}</p>
						{#if a.paragraphs.length > 1}<a class="more" href="/dictionary/{it.article}" lang={ta ? 'ta' : 'en'}>{ta ? 'மேலும் படிக்க' : 'Read more'} ›</a>{/if}
					{:catch}
						<p class="snippet muted">—</p>
					{/await}
				</li>
			{/each}
		</ul>
		{#if items.length > 12}<p class="muted small">+{items.length - 12}</p>{/if}
		<p class="credit">Easton's Bible Dictionary (1897), public domain · dataset by NEUU, CC BY 4.0</p>
	{/if}
</div>

<style>
	.dict { display: grid; gap: 0.9rem; padding-top: 0.6rem; }
	.hint { color: var(--muted); line-height: 1.7; margin: 0.8rem 0 0; font-size: 0.95rem; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.kicker { margin: 0.4rem 0 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.kicker .n { font-weight: 600; margin-left: 0.3rem; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; }
	.list li { padding: 0.7rem 0; border-top: 1px solid var(--line); display: grid; gap: 0.25rem; }
	.list li:first-child { border-top: 0; }
	.title { font-weight: 700; text-decoration: none; font-size: 1rem; }
	.snippet { margin: 0; font-size: 0.9rem; line-height: 1.6; color: var(--ink-2); font-family: var(--en); }
	.snippet[lang='ta'] { font-family: var(--tamil); font-size: 1rem; }
	.more { font-size: 0.82rem; font-weight: 600; text-decoration: none; }
	.more[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); }
	.small { font-size: 0.8rem; margin: 0; }
	.credit { margin: 0; font-size: 0.72rem; color: var(--muted); }
</style>

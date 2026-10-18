<script lang="ts">
	// Commentary sample: John 3:16 and what each commentary says on it, one tab
	// per commentary, cut short with a link to the verse page.
	import { findBook, findVersion, manifest, verseUrl } from '$lib/content/manifest';
	import { loadVerseCommentary, type VerseComment } from '$lib/commentary/verse';
	import CommentaryText from '$lib/commentary/CommentaryText.svelte';
	import Card from './Card.svelte';

	let { lang, versionPath }: { lang: 'ta' | 'en'; versionPath: string } = $props();
	const ta = $derived(lang === 'ta');
	const book = findBook('JHN')!;
	const version = $derived(findVersion(versionPath.split('+')[0]) ?? manifest.versions[0]);
	const href = $derived(verseUrl(versionPath.split('+')[0], book, 3, '16'));

	let verse = $state('');
	let comments = $state<VerseComment[]>([]);
	let pick = $state('');
	let done = $state(false);
	const shown = $derived(comments.find((c) => c.source.id === pick) ?? comments[0]);

	function load() {
		loadVerseCommentary(fetch, 'JHN', 3, 16, 16).then((all) => {
			const seen = new Set<string>();
			comments = all.filter((c) => !seen.has(c.source.id) && seen.add(c.source.id)).slice(0, 4);
			done = true;
		});
		fetch(`/api/verses?${new URLSearchParams({ v: version.code, ids: 'JHN.3.16' })}`)
			.then((r) => (r.ok ? r.json() : {}))
			.then((t: Record<string, string>) => (verse = t['JHN.3.16'] ?? ''))
			.catch(() => {});
	}
</script>

<Card ta="விளக்கவுரை" en="Commentary" tag={ta ? 'யோவான் 3:16' : 'John 3:16'} href={href} cta={ta ? 'முழு விளக்கவுரையைப் படிக்க' : 'Read the commentaries'} {lang} onvisible={load}>
	{#if verse}<blockquote lang={version.lang}><sup>16</sup> {verse}</blockquote>{/if}
	{#if comments.length}
		<div class="tabs" role="tablist" aria-label={ta ? 'விளக்கவுரை' : 'Commentary'}>
			{#each comments as c (c.source.id)}
				<button type="button" role="tab" aria-selected={c === shown} class:on={c === shown} onclick={() => (pick = c.source.id)}>{c.source.short}</button>
			{/each}
		</div>
		{#if shown}
			<div class="body" role="tabpanel">
				<p class="kicker">{shown.source.name} · {shown.source.year}</p>
				<div class="clip"><CommentaryText unit={shown.unit} {lang} {versionPath} compact /></div>
			</div>
		{/if}
	{:else if !done}
		<div class="ph" aria-hidden="true"></div>
	{/if}
</Card>

<style>
	blockquote { margin: 0; padding: 0.9rem 1.1rem; border-radius: var(--r-l); background: var(--hl); font-size: 1.05rem; line-height: 1.75; }
	blockquote[lang='ta'] { font-family: var(--tamil); }
	sup { color: var(--amber); font-weight: 700; font-family: var(--sans); font-size: 0.7rem; }
	.tabs { display: flex; flex-wrap: wrap; gap: 0.3rem; align-self: flex-start; padding: 4px; border-radius: var(--r); background: var(--surface-3); }
	.tabs button { border: 0; min-height: 40px; padding: 0 0.9rem; border-radius: 9px; background: transparent; color: var(--muted); font: 600 0.88rem var(--sans); cursor: pointer; }
	.tabs button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.body { display: flex; flex-direction: column; gap: 0.5rem; }
	.kicker { margin: 0; }
	.clip { max-height: 13rem; overflow: hidden; -webkit-mask-image: linear-gradient(#000 70%, transparent); mask-image: linear-gradient(#000 70%, transparent); }
	.ph { min-height: 12rem; border-radius: var(--r-l); background: var(--surface-2); }
</style>

<script lang="ts">
	// Cross-references for one verse, with the target text in the current version.
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { loadChapter } from '$lib/content/load';
	import type { ChapterJson, XrefTarget } from '$lib/content/types';

	let {
		verseId,
		targets,
		version,
		lang,
		onclose
	}: { verseId: string; targets: XrefTarget[]; version: string; lang: 'ta' | 'en'; onclose: () => void } = $props();

	const ta = $derived(lang === 'ta');
	let showAll = $state(false);
	const shown = $derived(showAll ? targets : targets.slice(0, 10));

	// Chapter cache so several references into one chapter cost one fetch.
	const chapterCache = new Map<string, Promise<ChapterJson>>();
	function chapter(code: string, ch: number) {
		const key = `${code}.${ch}`;
		if (!chapterCache.has(key)) chapterCache.set(key, loadChapter(fetch, version, code, ch));
		return chapterCache.get(key)!;
	}

	function parse(id: string) {
		const [code, ch, v] = id.split('.');
		return { code, ch: Number(ch), v: Number(v) };
	}
	function label(t: XrefTarget) {
		const a = parse(t.to);
		const book = findBook(a.code)!;
		const name = ta ? book.name_ta : book.name_en;
		if (!t.end) return `${name} ${a.ch}:${a.v}`;
		const b = parse(t.end);
		return a.ch === b.ch ? `${name} ${a.ch}:${a.v}-${b.v}` : `${name} ${a.ch}:${a.v}-${b.ch}:${b.v}`;
	}
	function href(t: XrefTarget) {
		const a = parse(t.to);
		const book = findBook(a.code)!;
		const range = t.end && parse(t.end).ch === a.ch && parse(t.end).v !== a.v ? `${a.v}-${parse(t.end).v}` : `${a.v}`;
		return chapterUrl(version.toLowerCase(), book, a.ch, range);
	}
	async function text(t: XrefTarget): Promise<string> {
		const a = parse(t.to);
		const end = t.end ? parse(t.end) : a;
		const ch = await chapter(a.code, a.ch);
		const last = end.ch === a.ch ? end.v : Number.MAX_SAFE_INTEGER;
		const parts: string[] = [];
		for (const b of ch.blocks) {
			if (b.type !== 'para') continue;
			for (const s of b.segments) {
				const n = Number(s.id?.split('.')[2]);
				if (n >= a.v && n <= last) parts.push(s.text);
			}
		}
		return parts.join(' ');
	}
	const verseLabel = $derived.by(() => {
		const a = parse(verseId);
		const book = findBook(a.code)!;
		return `${ta ? book.name_ta : book.name_en} ${a.ch}:${a.v}`;
	});
</script>

<aside class="xref-panel" aria-label={ta ? 'ஒப்புவசனங்கள்' : 'Cross-references'}>
	<header>
		<h2><span class="k">{ta ? 'ஒப்புவசனங்கள்' : 'Cross-references'}</span> {verseLabel}</h2>
		<button type="button" class="close" onclick={onclose} aria-label={ta ? 'மூடு' : 'Close'}>×</button>
	</header>
	<ol>
		{#each shown as t (t.to + (t.end ?? ''))}
			<li>
				<a href={href(t)} onclick={onclose}>{label(t)}</a>
				{#await text(t)}
					<p class="loading">…</p>
				{:then txt}
					<p lang={lang}>{txt}</p>
				{:catch}
					<p class="loading">—</p>
				{/await}
			</li>
		{/each}
	</ol>
	{#if targets.length > 10 && !showAll}
		<button type="button" class="more" onclick={() => (showAll = true)}>{ta ? `மேலும் ${targets.length - 10}` : `${targets.length - 10} more`}</button>
	{/if}
	<p class="credit">OpenBible.info, CC BY</p>
</aside>

<style>
	.xref-panel { position: fixed; z-index: 21; right: 0; top: 0; bottom: 0; width: min(24rem, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--line); padding: 1rem 1.2rem 2rem; box-shadow: -8px 0 30px rgba(0, 0, 0, 0.15); }
	header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
	h2 { font-size: 1rem; margin: 0.3rem 0 0.8rem; font-family: var(--tamil); }
	h2 .k { display: block; font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); font-family: var(--sans); }
	.close { border: 0; background: none; font-size: 1.6rem; line-height: 1; cursor: pointer; color: var(--muted); min-width: 44px; min-height: 44px; }
	ol { list-style: none; padding: 0; margin: 0; }
	li { padding: 0.6rem 0; border-top: 1px solid var(--line); }
	li a { font-weight: 600; text-decoration: none; font-family: var(--tamil); }
	li p { margin: 0.25rem 0 0; font-size: 0.95rem; }
	li p[lang='ta'] { font-family: var(--tamil); line-height: 1.8; }
	li p[lang='en'] { font-family: var(--serif); }
	.loading { color: var(--muted); }
	.more { margin-top: 0.8rem; padding: 0.45rem 0.9rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; cursor: pointer; }
	.credit { margin-top: 1.5rem; font-size: 0.75rem; color: var(--muted); }
</style>

<script lang="ts">
	// Cross-reference targets for one verse with the target text in the given
	// version. Shared by the overlay panel (phones) and the context panel (desktop).
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { loadChapter } from '$lib/content/load';
	import type { ChapterJson, XrefTarget } from '$lib/content/types';

	let {
		targets,
		version,
		lang,
		onnavigate
	}: { targets: XrefTarget[]; version: string; lang: 'ta' | 'en'; onnavigate?: () => void } = $props();

	const ta = $derived(lang === 'ta');
	let showAll = $state(false);
	const shown = $derived(showAll ? targets : targets.slice(0, 10));

	// Chapter cache so several references into one chapter cost one fetch.
	const chapterCache = new Map<string, Promise<ChapterJson>>();
	function chapter(code: string, ch: number) {
		const key = `${version}.${code}.${ch}`;
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
	function altBook(t: XrefTarget) {
		const book = findBook(parse(t.to).code)!;
		return ta ? book.name_en : book.name_ta;
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
	const textLang = $derived(version.toUpperCase().endsWith('TAM') || version.toUpperCase() === 'TCV' ? 'ta' : 'en');
</script>

<ol>
	{#each shown as t (t.to + (t.end ?? ''))}
		<li>
			<div class="ref">
				<a href={href(t)} onclick={() => onnavigate?.()} lang={ta ? 'ta' : 'en'}>{label(t)}</a>
				<span class="alt" lang={ta ? 'en' : 'ta'}>{altBook(t)}</span>
			</div>
			{#await text(t)}
				<p class="loading">…</p>
			{:then txt}
				<p lang={textLang}>{txt}</p>
			{:catch}
				<p class="loading">—</p>
			{/await}
		</li>
	{/each}
</ol>
{#if targets.length > 10 && !showAll}
	<button type="button" class="chip more" onclick={() => (showAll = true)}>{ta ? `மேலும் ${targets.length - 10}` : `${targets.length - 10} more`}</button>
{/if}
<p class="credit">OpenBible.info, CC BY</p>

<style>
	ol { list-style: none; padding: 0.6rem 0 0; margin: 0; display: grid; gap: 1.1rem; }
	li { --ref: var(--accent); border-left: 3px solid var(--ref); padding: 0.15rem 0 0.15rem 0.9rem; }
	li:nth-child(even) { --ref: var(--amber); }
	.ref { display: flex; justify-content: space-between; align-items: baseline; gap: 0.6rem; margin-bottom: 0.3rem; }
	.ref a { font-weight: 700; text-decoration: none; color: var(--ref); font-size: 0.98rem; }
	.ref a[lang='ta'] { font-family: var(--tamil); }
	.alt { font-size: 0.72rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); }
	li p { margin: 0; font-size: 1.05rem; line-height: 1.75; }
	li p[lang='ta'] { font-family: var(--tamil); font-size: 1.15rem; line-height: 1.8; }
	li p[lang='en'] { font-family: var(--en); color: var(--ink-en); }
	.loading { color: var(--muted); }
	.more { margin-top: 1rem; }
	.credit { margin-top: 1.5rem; font-size: 0.72rem; color: var(--muted); }
</style>

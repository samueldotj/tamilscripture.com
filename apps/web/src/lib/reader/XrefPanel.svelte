<script lang="ts">
	// Cross-references for one verse, with the target text in the current version.
	// Desktop: a right-hand panel (design 3A); phones: a bottom sheet (design 04).
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
	const verseLabel = $derived.by(() => {
		const a = parse(verseId);
		const book = findBook(a.code)!;
		return `${ta ? book.name_ta : book.name_en} ${a.ch}:${a.v}`;
	});
	const textLang = $derived(version.toUpperCase().endsWith('TAM') || version.toUpperCase() === 'TCV' ? 'ta' : 'en');
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onclose} onkeydown={onKey}></div>
<div class="xref-panel" aria-label={ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'} role="dialog" tabindex="-1" onkeydown={onKey}>
	<span class="grab" aria-hidden="true"></span>
	<header>
		<div>
			<div class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'தொடர்புள்ள வசனங்கள்' : 'Related verses'}</div>
			<h2 lang={ta ? 'ta' : 'en'}>{verseLabel} <span class="count">· {targets.length} {ta ? 'குறிப்புகள்' : 'refs'}</span></h2>
		</div>
		<button type="button" class="close" onclick={onclose} aria-label={ta ? 'மூடு' : 'Close'}>✕</button>
	</header>
	<ol>
		{#each shown as t (t.to + (t.end ?? ''))}
			<li>
				<div class="ref">
					<a href={href(t)} onclick={onclose} lang={ta ? 'ta' : 'en'}>{label(t)}</a>
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
</div>

<style>
	.backdrop { position: fixed; inset: 0; z-index: 20; background: transparent; }
	.xref-panel { position: fixed; z-index: 21; right: 0; top: 0; bottom: 0; width: min(26rem, 100%); overflow-y: auto; background: var(--surface); border-left: var(--bw) solid var(--line); padding: 1.1rem 1.4rem 2rem; box-shadow: var(--shadow-lg); }
	.grab { display: none; }
	header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; padding-bottom: 0.9rem; margin-bottom: 0.4rem; border-bottom: var(--bw) solid var(--line); }
	h2 { font-size: 1.2rem; margin: 0.15rem 0 0; font-weight: 600; }
	h2[lang='ta'] { font-family: var(--tamil); }
	.count { font-size: 0.8rem; color: var(--muted); font-weight: 400; font-family: var(--sans); }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.close { flex: none; width: 40px; height: 40px; border-radius: 999px; border: 0; background: var(--surface-2); color: var(--ink-2); font-size: 0.95rem; cursor: pointer; }
	.close:hover { color: var(--ink); }
	ol { list-style: none; padding: 0; margin: 0; display: grid; gap: 1.1rem; padding-top: 0.6rem; }
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
	@media (max-width: 720px) {
		.backdrop { background: var(--scrim); }
		.xref-panel { top: 18%; width: 100%; border-left: 0; border-top: var(--bw) solid var(--line-2); border-radius: 26px 26px 0 0; padding-top: 0.75rem; }
		.grab { display: block; width: 44px; height: 5px; border-radius: 999px; background: var(--line-2); margin: 0 auto 0.8rem; }
	}
</style>

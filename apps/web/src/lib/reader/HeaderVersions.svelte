<script lang="ts">
	// The translation (and a second to compare with) in the site header on chapter pages,
	// beside the reference box. The header stays at the top while the reader's own
	// toolbar, above the previous chapter's greyed ending (continuous scrolling), cannot
	// be scrolled back to without opening that chapter.
	import { goto } from '$app/navigation';
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import type { Book, VersionMeta } from '$lib/content/types';

	let { versions, book, chapter, lang }: { versions: VersionMeta[]; book: Book; chapter: number; lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');
	const secondary = $derived(versions[1]?.code ?? '');

	function go(codes: string[]) {
		goto(chapterUrl(codes.map((x) => x.toLowerCase()).join('+'), book, chapter));
	}
	function onVersion(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		go([code, ...versions.slice(1).map((v) => v.code).filter((v) => v !== code)]);
	}
	function onCompare(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		go(code ? [versions[0].code, code] : [versions[0].code]);
	}
</script>

<div class="versions" role="group" aria-label={ta ? 'மொழிபெயர்ப்பு' : 'Translation'}>
	<select class="chip" aria-label={ta ? 'மொழிபெயர்ப்பு' : 'Version'} title={ta ? 'மொழிபெயர்ப்பு' : 'Translation'} value={versions[0].code} onchange={onVersion}>
		{#each manifest.versions as v (v.code)}
			<option value={v.code} disabled={!v.books.includes(book.code)}>{v.short}</option>
		{/each}
	</select>
	<select class="chip compare" class:dashed={!secondary} aria-label={ta ? 'ஒப்பிடு' : 'Compare with'} value={secondary} onchange={onCompare}>
		<option value="">{ta ? '+ ஒப்பிடு' : '+ compare'}</option>
		{#each manifest.versions.filter((v) => v.code !== versions[0].code) as v (v.code)}
			<option value={v.code} disabled={!v.books.includes(book.code)}>{v.short}</option>
		{/each}
	</select>
</div>

<style>
	.versions { display: flex; gap: 0.5rem; flex: none; }
	select.chip { padding: 0.5rem 0.75rem; min-height: 42px; font-family: var(--sans); }
	select.chip option { font-weight: 400; }
	.compare.dashed { color: var(--accent); }
	/* Phones choose the version from the chapter pill's menu. */
	@media (max-width: 720px) { .versions { display: none; } }
</style>

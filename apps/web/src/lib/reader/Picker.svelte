<script lang="ts">
	// Compact version / compare / book / chapter picker that mirrors the current position.
	import { goto } from '$app/navigation';
	import { chapterUrl, manifest } from '$lib/content/manifest';
	import type { Book, VersionMeta } from '$lib/content/types';

	let {
		versions,
		book,
		chapter,
		lang
	}: { versions: VersionMeta[]; book: Book; chapter?: number; lang: 'ta' | 'en' } = $props();

	const ta = $derived(lang === 'ta');
	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');
	const secondary = $derived(versions[1]?.code ?? '');

	function go(codes: string[], b: Book, c?: number) {
		goto(chapterUrl(codes.map((x) => x.toLowerCase()).join('+'), b, c));
	}
	function onVersion(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		const rest = versions.slice(1).map((v) => v.code).filter((v) => v !== code);
		go([code, ...rest], book, chapter);
	}
	function onCompare(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		go(code ? [versions[0].code, code] : [versions[0].code], book, chapter);
	}
	function onBook(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		go(versions.map((v) => v.code), manifest.books.find((x) => x.code === code)!, 1);
	}
	function onChapter(e: Event) {
		go(versions.map((v) => v.code), book, Number((e.currentTarget as HTMLSelectElement).value));
	}
</script>

<div class="picker" role="group" aria-label={ta ? 'இடம் தேர்வு' : 'Choose passage'}>
	<select class="chip" aria-label={ta ? 'மொழிபெயர்ப்பு' : 'Version'} value={versions[0].code} onchange={onVersion}>
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
	<select class="chip" aria-label={ta ? 'புத்தகம்' : 'Book'} value={book.code} onchange={onBook} lang={ta ? 'ta' : 'en'}>
		<optgroup label={ta ? 'பழைய ஏற்பாடு' : 'Old Testament'}>
			{#each ot as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
		</optgroup>
		<optgroup label={ta ? 'புதிய ஏற்பாடு' : 'New Testament'}>
			{#each nt as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
		</optgroup>
	</select>
	{#if chapter !== undefined}
		<select class="chip" aria-label={ta ? 'அதிகாரம்' : 'Chapter'} value={String(chapter)} onchange={onChapter}>
			{#each Array.from({ length: book.chapters }, (_, i) => i + 1) as c (c)}
				<option value={String(c)}>{c}</option>
			{/each}
		</select>
	{/if}
</div>

<style>
	.picker { display: flex; gap: 0.6rem; flex-wrap: wrap; }
	select.chip { padding: 0.5rem 0.75rem; max-width: 100%; font-family: var(--sans); }
	select.chip[lang='ta'] { font-family: var(--tamil); }
	select.chip option { font-weight: 400; }
	.compare.dashed { color: var(--accent); }
</style>

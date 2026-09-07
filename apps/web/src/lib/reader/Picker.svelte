<script lang="ts">
	// Compact version / book / chapter picker that mirrors the current position.
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
	const versionPath = $derived(versions.map((v) => v.code.toLowerCase()).join('+'));
	const ot = manifest.books.filter((b) => b.testament === 'OT');
	const nt = manifest.books.filter((b) => b.testament === 'NT');

	function go(vp: string, b: Book, c?: number) {
		goto(chapterUrl(vp, b, c));
	}
	function onVersion(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		// Replace the primary version, keep a second one if present.
		const rest = versions.slice(1).map((v) => v.code.toLowerCase());
		go([code, ...rest].join('+'), book, chapter);
	}
	function onBook(e: Event) {
		const code = (e.currentTarget as HTMLSelectElement).value;
		const b = manifest.books.find((x) => x.code === code)!;
		go(versionPath, b, 1);
	}
	function onChapter(e: Event) {
		go(versionPath, book, Number((e.currentTarget as HTMLSelectElement).value));
	}
</script>

<div class="picker" role="group" aria-label={ta ? 'இடம் தேர்வு' : 'Choose passage'}>
	<select aria-label={ta ? 'மொழிபெயர்ப்பு' : 'Version'} value={versions[0].code} onchange={onVersion}>
		{#each manifest.versions as v (v.code)}
			<option value={v.code} disabled={!v.books.includes(book.code)}>{v.short}</option>
		{/each}
	</select>
	<select aria-label={ta ? 'புத்தகம்' : 'Book'} value={book.code} onchange={onBook} lang={ta ? 'ta' : 'en'}>
		<optgroup label={ta ? 'பழைய ஏற்பாடு' : 'Old Testament'}>
			{#each ot as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
		</optgroup>
		<optgroup label={ta ? 'புதிய ஏற்பாடு' : 'New Testament'}>
			{#each nt as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
		</optgroup>
	</select>
	{#if chapter !== undefined}
		<select aria-label={ta ? 'அதிகாரம்' : 'Chapter'} value={String(chapter)} onchange={onChapter}>
			{#each Array.from({ length: book.chapters }, (_, i) => i + 1) as c (c)}
				<option value={String(c)}>{c}</option>
			{/each}
		</select>
	{/if}
</div>

<style>
	.picker { display: flex; gap: 0.4rem; flex-wrap: wrap; }
	select { font: inherit; font-size: 0.92rem; padding: 0.4rem 0.5rem; min-height: 40px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; max-width: 100%; }
	select[lang='ta'] { font-family: var(--tamil); }
</style>

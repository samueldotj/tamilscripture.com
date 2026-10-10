<script lang="ts">
	// Actions for the current verse selection, as icons to keep the bar small: play, highlight
	// (one swatch that opens the colours), note, bookmark, the Hebrew or Greek words, the
	// verse's places on the map and its persons, copy, share (as an image), clear.
	// `floating` is the pill over the text (phones, tablets); `panel` lays the
	// same controls out inside the desktop context column.
	import type { ChapterJson, Book } from '$lib/content/types';
	import { chapterUrl, verseUrl } from '$lib/content/manifest';
	import { COLORS, type HighlightColor } from '$lib/personal/repo';

	let {
		selected,
		chapter,
		book,
		versionPath,
		versionShort,
		lang,
		signedIn = false,
		currentColor = null,
		excerpt = '',
		communityUsers = 0,
		variant = 'floating',
		onclear,
		onhighlight,
		onnote,
		bookmarked = false,
		onbookmark,
		onoriginal,
		onplayfrom,
		onmap,
		onpersons
	}: {
		selected: Set<string>;
		chapter: ChapterJson;
		book: Book;
		versionPath: string;
		versionShort: string;
		lang: 'ta' | 'en';
		signedIn?: boolean;
		currentColor?: HighlightColor | null;
		/** The selected words when the selection is part of a verse (R-10.15); highlight and note apply to them. */
		excerpt?: string;
		/** readers who highlighted the selected verse (max over the selection); 0 when below the privacy threshold */
		communityUsers?: number;
		variant?: 'floating' | 'panel';
		onclear: () => void;
		onhighlight?: (color: HighlightColor | null) => void;
		onnote?: () => void;
		/** Whether the first selected verse is bookmarked; the button toggles it. */
		bookmarked?: boolean;
		onbookmark?: () => void;
		/** Opens the Hebrew or Greek words of the selection. */
		onoriginal?: () => void;
		/** Play the recording from the first selected verse (timed recordings only, design 12A). */
		onplayfrom?: () => void;
		/** Show the selected verses' places on the chapter map; absent when they name none. */
		onmap?: () => void;
		/** Show the persons the selected verses name; absent when they name none. */
		onpersons?: () => void;
	} = $props();

	let toast = $state('');
	const ta = $derived(lang === 'ta');

	const numbers = $derived(
		[...selected].map((id) => Number(id.split('.')[2])).filter((n) => !isNaN(n)).sort((a, b) => a - b)
	);
	const rangeText = $derived.by(() => {
		if (!numbers.length) return '';
		const parts: string[] = [];
		let start = numbers[0], prev = numbers[0];
		for (const n of numbers.slice(1).concat(NaN)) {
			if (n === prev + 1) { prev = n; continue; }
			parts.push(start === prev ? `${start}` : `${start}-${prev}`);
			start = prev = n;
		}
		return parts.join(',');
	});
	const contiguous = $derived(numbers.length > 0 && numbers[numbers.length - 1] - numbers[0] === numbers.length - 1);
	const bookName = $derived(ta ? book.name_ta : book.name_en);
	const label = $derived(`${bookName} ${chapter.chapter}:${rangeText}`);
	const verses = $derived(contiguous ? (numbers.length === 1 ? `${numbers[0]}` : `${numbers[0]}-${numbers[numbers.length - 1]}`) : `${numbers[0]}`);
	const url = $derived(`https://www.tamilscripture.com${chapterUrl(versionPath, book, chapter.chapter, verses)}`);
	/** The single-verse page: the selection alone, large, in Tamil and English. */
	const largePath = $derived(verseUrl(versionPath, book, chapter.chapter, verses));

	function selectedText(): string {
		const out: string[] = [];
		for (const b of chapter.blocks) {
			if (b.type !== 'para') continue;
			for (const s of b.segments) {
				if (s.id && selected.has(s.id)) out.push((s.n ? `${s.n} ` : '') + s.text);
			}
		}
		return `${out.join(' ')}\n— ${label} (${versionShort})\n${url}`;
	}
	async function copy() {
		try { await navigator.clipboard.writeText(selectedText()); flash(ta ? 'நகலெடுக்கப்பட்டது' : 'Copied'); }
		catch { flash(ta ? 'நகலெடுக்க முடியவில்லை' : 'Could not copy'); }
	}
	function flash(msg: string) { toast = msg; setTimeout(() => (toast = ''), 1800); }
	const colorNames: Record<HighlightColor, [string, string]> = {
		yellow: ['மஞ்சள்', 'Yellow'], green: ['பச்சை', 'Green'], blue: ['நீலம்', 'Blue'], pink: ['இளஞ்சிவப்பு', 'Pink']
	};
	// The highlight swatch opens the four colours, and a way to take the highlight off.
	let colorsOpen = $state(false);
	let colorBox = $state<HTMLElement>();
	function closeColors(e: Event) {
		if (colorsOpen && colorBox && !colorBox.contains(e.target as Node)) colorsOpen = false;
	}
	function pickColor(c: HighlightColor | null) {
		colorsOpen = false;
		onhighlight?.(c);
	}
	const nt = $derived(book.testament === 'NT');
	const originalName = $derived(nt ? (ta ? 'கிரேக்கச் சொற்கள்' : 'Greek words') : (ta ? 'எபிரெயச் சொற்கள்' : 'Hebrew words'));
	const signinHref = $derived(`/signin?next=${encodeURIComponent(location.pathname)}`);
</script>

<svelte:window onpointerdown={closeColors} onkeydown={(e) => { if (e.key === 'Escape') colorsOpen = false; }} />

{#snippet icon(paths: string[], fill = false)}
	<svg width="20" height="20" viewBox="0 0 24 24" fill={fill ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{#each paths as d (d)}<path {d}></path>{/each}</svg>
{/snippet}
{#snippet pencil()}{@render icon(['M21.17 6.81a1 1 0 0 0-3.98-3.98L3.84 16.17a2 2 0 0 0-.5.83l-1.32 4.35a.5.5 0 0 0 .62.62l4.35-1.32a2 2 0 0 0 .83-.5z', 'm15 5 4 4'])}{/snippet}

{#if selected.size}
	<div class="bar" class:card={variant === 'floating'} class:floating={variant === 'floating'} class:panel={variant === 'panel'} role="toolbar" aria-label={ta ? 'வசனச் செயல்கள்' : 'Verse actions'}>
		<span class="label" lang={lang}>{label}</span>
		{#if excerpt}
			<span class="excerpt" title={excerpt}>“{excerpt}”</span>
		{/if}
		{#if communityUsers}
			<span class="community" title={ta ? `${communityUsers} வாசகர்கள் அடிக்கோடிட்டனர்` : `${communityUsers} readers highlighted this`}>◉ {communityUsers}</span>
		{/if}
		<span class="icons">
			{#if onplayfrom && numbers.length}
				{@const t = ta ? `${chapter.chapter}:${numbers[0]} முதல் கேள்` : `Play from ${chapter.chapter}:${numbers[0]}`}
				<button type="button" class="ic play" onclick={() => onplayfrom?.()} aria-label={t} title={t}>{@render icon(['M6 3l14 9-14 9z'], true)}</button>
			{/if}
			{#if signedIn}
				<span class="hl" bind:this={colorBox}>
					<button type="button" class="ic" aria-label={ta ? 'அடிக்கோடு' : 'Highlight'} title={ta ? 'அடிக்கோடு' : 'Highlight'} aria-haspopup="true" aria-expanded={colorsOpen} onclick={() => (colorsOpen = !colorsOpen)}><span class="swatch {currentColor ?? 'green'}" class:on={!!currentColor}></span></button>
					{#if colorsOpen}
						<span class="colors card" role="group" aria-label={ta ? 'அடிக்கோடு நிறம்' : 'Highlight colour'}>
							{#each COLORS as c (c)}
								<button type="button" class="swatch {c}" class:on={currentColor === c} aria-label={ta ? colorNames[c][0] : colorNames[c][1]} aria-pressed={currentColor === c} onclick={() => pickColor(currentColor === c ? null : c)}></button>
							{/each}
							{#if currentColor}
								<button type="button" class="swatch none" aria-label={ta ? 'அடிக்கோட்டை நீக்கு' : 'Remove highlight'} title={ta ? 'அடிக்கோட்டை நீக்கு' : 'Remove highlight'} onclick={() => pickColor(null)}>✕</button>
							{/if}
						</span>
					{/if}
				</span>
				<button type="button" class="ic" onclick={() => onnote?.()} aria-label={ta ? 'குறிப்பு' : 'Note'} title={ta ? 'குறிப்பு' : 'Note'}>{@render pencil()}</button>
				{#if onbookmark}
					<button type="button" class="ic" class:marked={bookmarked} aria-pressed={bookmarked} onclick={() => onbookmark?.()} aria-label={ta ? 'குறி' : 'Bookmark'} title={ta ? 'குறி' : 'Bookmark'}>{@render icon(['M12 2.5l2.9 5.9 6.5.9-4.7 4.6 1.1 6.5L12 17.3l-5.8 3.1 1.1-6.5L2.6 9.3l6.5-.9z'], bookmarked)}</button>
				{/if}
			{:else}
				<a class="ic" href={signinHref} aria-label={ta ? 'அடிக்கோடு (உள்நுழைக)' : 'Highlight (sign in)'} title={ta ? 'அடிக்கோடு' : 'Highlight'}><span class="swatch green"></span></a>
				<a class="ic" href={signinHref} aria-label={ta ? 'குறிப்பு (உள்நுழைக)' : 'Note (sign in)'} title={ta ? 'குறிப்பு' : 'Note'}>{@render pencil()}</a>
			{/if}
			{#if onoriginal}
				<!-- The first letter of the original language: aleph for the Old Testament, alpha for the New. -->
				<button type="button" class="ic letter" onclick={() => onoriginal?.()} aria-label={originalName} title={originalName}><span aria-hidden="true" lang={nt ? 'el' : 'he'}>{nt ? 'α' : 'א'}</span></button>
			{/if}
			{#if onmap}
				<button type="button" class="ic" onclick={() => onmap?.()} aria-label={ta ? 'வரைபடம்' : 'Map'} title={ta ? 'வரைபடம்' : 'Map'}>{@render icon(['M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z', 'M9 3v15', 'M15 6v15'])}</button>
			{/if}
			{#if onpersons}
				<button type="button" class="ic" onclick={() => onpersons?.()} aria-label={ta ? 'நபர்கள்' : 'Persons'} title={ta ? 'நபர்கள்' : 'Persons'}>{@render icon(['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2', 'M9 3a4 4 0 1 0 0 8 4 4 0 1 0 0-8', 'M22 21v-2a4 4 0 0 0-3-3.87', 'M16 3.13a4 4 0 0 1 0 7.75'])}</button>
			{/if}
			<button type="button" class="ic" onclick={copy} aria-label={ta ? 'நகல்' : 'Copy'} title={ta ? 'நகல்' : 'Copy'}>{@render icon(['M10 8h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2z', 'M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2'])}</button>
			<!-- Share goes straight to the verse's image: the picture, its text and the link go out from there. -->
			<a class="ic" href="{largePath}#image" aria-label={ta ? 'பகிர்' : 'Share'} title={ta ? 'பகிர்' : 'Share'}>{@render icon(['M18 2a3 3 0 1 0 0 6 3 3 0 1 0 0-6', 'M6 9a3 3 0 1 0 0 6 3 3 0 1 0 0-6', 'M18 16a3 3 0 1 0 0 6 3 3 0 1 0 0-6', 'm8.59 13.51 6.83 3.98', 'M15.41 6.51l-6.82 3.98'])}</a>
			<button type="button" class="ic ghost" onclick={onclear} aria-label={ta ? 'தெரிவை நீக்கு' : 'Clear selection'}>✕</button>
		</span>
		{#if toast}<span class="toast" role="status">{toast}</span>{/if}
	</div>
{/if}

<style>
	.bar { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
	.floating { position: fixed; left: 50%; bottom: calc(max(1rem, env(safe-area-inset-bottom)) + var(--player-h, 0px)); transform: translateX(-50%); z-index: 15; padding: 0.35rem 0.35rem 0.35rem 0.9rem; border-color: var(--line-2); border-radius: var(--r-2xl); box-shadow: var(--shadow); width: max-content; max-width: calc(100vw - 1.5rem); justify-content: center; }
	/* On a phone the label takes its own line and the icons fit one row beneath it. */
	@media (max-width: 480px) {
		.floating { padding: 0.45rem 0.3rem 0.3rem; row-gap: 0.15rem; }
		.floating .ic { width: 36px; }
		.floating .icons { flex-wrap: nowrap; }
	}
	.panel { position: relative; }
	.panel .label { display: none; }
	.label { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 40vw; }
	.label[lang='ta'] { font-family: var(--tamil); }
	.icons { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 0.1rem; }
	.panel .icons { width: 100%; justify-content: flex-start; gap: 0.35rem; }
	.ic { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; min-height: 40px; padding: 0; border: 0; border-radius: 999px; background: none; color: var(--ink-2); cursor: pointer; text-decoration: none; }
	.panel .ic { width: 44px; height: 44px; border: var(--bw) solid var(--line); }
	.ic:hover { background: var(--surface-2); color: var(--ink); }
	.ic.play { background: var(--accent); color: var(--on-accent); }
	.ic.play:hover { background: var(--accent); color: var(--on-accent); filter: brightness(1.08); }
	.ic.marked { color: var(--amber); }
	.ic.letter span { font-family: 'SBL Hebrew', 'Ezra SIL', 'Times New Roman', serif; font-size: 1.3rem; font-weight: 700; line-height: 1; }
	.ic.letter span:lang(el) { font-family: 'Gentium Plus', 'Times New Roman', serif; font-size: 1.4rem; font-style: italic; }
	.ghost { color: var(--muted); font-size: 0.95rem; }
	.excerpt { font-family: var(--tamil); font-style: italic; font-size: 0.85rem; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 14rem; }
	.panel .excerpt { width: 100%; max-width: none; white-space: normal; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; line-clamp: 3; }
	.community { font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
	.panel .community { width: 100%; }
	.hl { position: relative; display: inline-flex; }
	.colors { position: absolute; bottom: calc(100% + 0.6rem); left: 50%; transform: translateX(-50%); z-index: 20; display: flex; gap: 0.45rem; padding: 0.5rem 0.6rem; border-radius: 999px; box-shadow: var(--shadow); }
	.panel .colors { bottom: auto; top: calc(100% + 0.4rem); left: 0; transform: none; }
	.swatch { display: block; width: 22px; height: 22px; min-height: 22px; padding: 0; border-radius: 50%; border: 2px solid transparent; }
	.colors .swatch { width: 30px; height: 30px; min-height: 30px; cursor: pointer; }
	.swatch.yellow { background: var(--swatch-yellow); } .swatch.green { background: var(--swatch-green); } .swatch.blue { background: var(--swatch-blue); } .swatch.pink { background: var(--swatch-pink); }
	.swatch.on { border-color: var(--ink); }
	.swatch.none { display: inline-flex; align-items: center; justify-content: center; background: var(--surface-2); color: var(--muted); font-size: 0.8rem; border-color: var(--line-2); }
	.toast { position: absolute; bottom: calc(100% + 0.5rem); left: 50%; transform: translateX(-50%); background: var(--ink); color: var(--bg); font-size: 0.85rem; padding: 0.4rem 0.8rem; border-radius: var(--r-s); white-space: nowrap; }
</style>

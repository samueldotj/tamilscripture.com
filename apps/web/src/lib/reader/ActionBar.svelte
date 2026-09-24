<script lang="ts">
	// Actions for the current verse selection: highlight, note, copy, share, clear.
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
		onoriginal
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
		/** Opens the Hebrew or Greek words of the selection (phones; the panel has a tab). */
		onoriginal?: () => void;
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
	// Share opens a small menu: the verse in its chapter, or the large single-verse page.
	let shareOpen = $state(false);
	let shareBox = $state<HTMLElement>();
	async function share(large = false) {
		shareOpen = false;
		const link = large ? `https://www.tamilscripture.com${largePath}` : url;
		const data = large ? { title: label, text: label, url: link } : { title: label, text: selectedText(), url };
		if (navigator.share) { try { await navigator.share(data); } catch { /* cancelled */ } }
		else { try { await navigator.clipboard.writeText(link); flash(ta ? 'இணைப்பு நகலெடுக்கப்பட்டது' : 'Link copied'); } catch { flash(link); } }
	}
	function closeShare(e: Event) {
		if (shareOpen && shareBox && !shareBox.contains(e.target as Node)) shareOpen = false;
	}
	function flash(msg: string) { toast = msg; setTimeout(() => (toast = ''), 1800); }
	const colorNames: Record<HighlightColor, [string, string]> = {
		yellow: ['மஞ்சள்', 'Yellow'], green: ['பச்சை', 'Green'], blue: ['நீலம்', 'Blue'], pink: ['இளஞ்சிவப்பு', 'Pink']
	};
	const signinHref = $derived(`/signin?next=${encodeURIComponent(location.pathname)}`);
</script>

<svelte:window onpointerdown={closeShare} onkeydown={(e) => { if (e.key === 'Escape') shareOpen = false; }} />

{#if selected.size}
	<div class="bar" class:card={variant === 'floating'} class:floating={variant === 'floating'} class:panel={variant === 'panel'} role="toolbar" aria-label={ta ? 'வசனச் செயல்கள்' : 'Verse actions'}>
		<span class="label" lang={lang}>{label}</span>
		{#if excerpt}
			<span class="excerpt" title={excerpt}>“{excerpt}”</span>
		{/if}
		{#if communityUsers}
			<span class="community" title={ta ? `${communityUsers} வாசகர்கள் அடிக்கோடிட்டனர்` : `${communityUsers} readers highlighted this`}>◉ {communityUsers}</span>
		{/if}
		{#if signedIn}
			<span class="colors" role="group" aria-label={ta ? 'அடிக்கோடு' : 'Highlight'}>
				{#each COLORS as c (c)}
					<button type="button" class="swatch {c}" class:on={currentColor === c} aria-label={ta ? colorNames[c][0] : colorNames[c][1]} aria-pressed={currentColor === c} onclick={() => onhighlight?.(currentColor === c ? null : c)}></button>
				{/each}
			</span>
			<button type="button" class="chip primary" onclick={() => onnote?.()}>{ta ? 'குறிப்பு' : 'Note'}</button>
		{:else}
			<a class="chip primary" href={signinHref}>{ta ? 'அடிக்கோடு · குறிப்பு' : 'Highlight · Note'}</a>
		{/if}
		{#if onoriginal}
			<button type="button" class="chip" onclick={() => onoriginal?.()} lang="ta" title={ta ? 'எபிரெய / கிரேக்கச் சொற்கள்' : 'Hebrew / Greek words'}>மூலம்</button>
		{/if}
		<button type="button" class="chip" onclick={copy}>{ta ? 'நகல்' : 'Copy'}</button>
		<span class="share" bind:this={shareBox}>
			<button type="button" class="chip" aria-haspopup="menu" aria-expanded={shareOpen} onclick={() => (shareOpen = !shareOpen)}>{ta ? 'பகிர்' : 'Share'} <span aria-hidden="true">▾</span></button>
			{#if shareOpen}
				<div class="menu card" role="menu" lang={lang}>
					<button type="button" role="menuitem" onclick={() => share()}>
						{ta ? 'அதிகாரத்தில் வசனம்' : 'Verse in its chapter'}
						<small>{ta ? 'சுற்றியுள்ள வசனங்களுடன்' : 'With the verses around it'}</small>
					</button>
					<button type="button" role="menuitem" onclick={() => share(true)}>
						{ta ? 'பெரிய எழுத்தில்' : 'Large text'}
						<small>{ta ? 'இந்த வசனம் மட்டும், தமிழும் ஆங்கிலமும்' : 'Just this verse, in Tamil and English'}</small>
					</button>
					<a role="menuitem" href={largePath} onclick={() => (shareOpen = false)}>{ta ? 'பெரிய எழுத்தில் திற' : 'Open large text'} <span aria-hidden="true">↗</span></a>
				</div>
			{/if}
		</span>
		<button type="button" class="ghost" onclick={onclear} aria-label={ta ? 'தெரிவை நீக்கு' : 'Clear selection'}>✕</button>
		{#if toast}<span class="toast" role="status">{toast}</span>{/if}
	</div>
{/if}

<style>
	.bar { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
	.floating { position: fixed; left: 50%; bottom: max(1rem, env(safe-area-inset-bottom)); transform: translateX(-50%); z-index: 15; padding: 0.6rem 0.6rem 0.6rem 1rem; border-color: var(--line-2); border-radius: var(--r-2xl); box-shadow: var(--shadow); max-width: calc(100vw - 1.5rem); justify-content: center; }
	.panel { position: relative; }
	.panel .label { display: none; }
	.label { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 40vw; }
	.label[lang='ta'] { font-family: var(--tamil); }
	.chip { min-height: 40px; padding: 0.4rem 0.85rem; border-radius: var(--r); }
	.panel .chip { flex: 1 1 auto; min-height: 46px; }
	.ghost { border: 0; background: none; color: var(--muted); font-size: 0.95rem; line-height: 1; min-width: 40px; min-height: 40px; padding: 0; cursor: pointer; border-radius: 999px; }
	.ghost:hover { background: var(--surface-2); color: var(--ink); }
	.excerpt { font-family: var(--tamil); font-style: italic; font-size: 0.85rem; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 14rem; }
	.panel .excerpt { width: 100%; max-width: none; white-space: normal; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; line-clamp: 3; }
	.community { font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
	.panel .community { width: 100%; }
	.colors { display: inline-flex; gap: 0.35rem; padding: 0 0.2rem; }
	.panel .colors { width: 100%; gap: 0.5rem; padding: 0 0 0.2rem; }
	.swatch { width: 28px; height: 28px; min-height: 28px; padding: 0; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
	.panel .swatch { width: 32px; height: 32px; min-height: 32px; }
	.swatch.yellow { background: var(--hl-yellow); } .swatch.green { background: var(--hl-green); } .swatch.blue { background: var(--hl-blue); } .swatch.pink { background: var(--hl-pink); }
	.swatch.on { border-color: var(--ink); }
	.share { position: relative; display: inline-flex; }
	.panel .share { flex: 1 1 auto; }
	/* The floating pill is centred on screen; centring the menu over it keeps it on a phone's screen. */
	.floating .share { position: static; }
	.floating .menu { left: 50%; right: auto; transform: translateX(-50%); min-width: 0; width: min(18rem, calc(100vw - 1.5rem)); }
	.panel .share > .chip { width: 100%; }
	.menu { position: absolute; bottom: calc(100% + 0.5rem); right: 0; z-index: 20; min-width: 15rem; padding: 0.35rem; display: flex; flex-direction: column; box-shadow: var(--shadow); }
	.menu button, .menu a { display: flex; flex-direction: column; align-items: flex-start; gap: 0.1rem; min-height: 44px; padding: 0.55rem 0.75rem; border: 0; border-radius: var(--r-s); background: none; color: var(--ink); font: inherit; font-weight: 600; text-align: left; text-decoration: none; cursor: pointer; }
	.menu a { flex-direction: row; align-items: center; gap: 0.35rem; color: var(--accent); border-top: 1px solid var(--line); border-radius: 0 0 var(--r-s) var(--r-s); }
	.menu button:hover, .menu a:hover { background: var(--surface-2); }
	.menu small { font-weight: 400; font-size: 0.8rem; color: var(--muted); }
	.menu[lang='ta'] { font-family: var(--tamil); }
	.toast { position: absolute; bottom: calc(100% + 0.5rem); left: 50%; transform: translateX(-50%); background: var(--ink); color: var(--bg); font-size: 0.85rem; padding: 0.4rem 0.8rem; border-radius: var(--r-s); white-space: nowrap; }
</style>

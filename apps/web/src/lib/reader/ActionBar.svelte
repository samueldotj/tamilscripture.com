<script lang="ts">
	// Floating actions for the current verse selection: copy text, share link, clear.
	import type { ChapterJson } from '$lib/content/types';
	import type { Book } from '$lib/content/types';
	import { chapterUrl } from '$lib/content/manifest';

	let {
		selected,
		chapter,
		book,
		versionPath,
		versionShort,
		lang,
		onclear
	}: {
		selected: Set<string>;
		chapter: ChapterJson;
		book: Book;
		versionPath: string;
		versionShort: string;
		lang: 'ta' | 'en';
		onclear: () => void;
	} = $props();

	let toast = $state('');
	const ta = $derived(lang === 'ta');

	// Verse numbers in the selection, sorted; range string like "16-18" or "3,5".
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
	const url = $derived(
		`https://www.tamilscripture.com${chapterUrl(versionPath, book, chapter.chapter, contiguous ? (numbers.length === 1 ? `${numbers[0]}` : `${numbers[0]}-${numbers[numbers.length - 1]}`) : `${numbers[0]}`)}`
	);

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
		try {
			await navigator.clipboard.writeText(selectedText());
			flash(ta ? 'நகலெடுக்கப்பட்டது' : 'Copied');
		} catch {
			flash(ta ? 'நகலெடுக்க முடியவில்லை' : 'Could not copy');
		}
	}

	async function share() {
		const data = { title: label, text: selectedText(), url };
		if (navigator.share) {
			try { await navigator.share(data); } catch { /* cancelled */ }
		} else {
			try {
				await navigator.clipboard.writeText(url);
				flash(ta ? 'இணைப்பு நகலெடுக்கப்பட்டது' : 'Link copied');
			} catch { flash(url); }
		}
	}

	function flash(msg: string) {
		toast = msg;
		setTimeout(() => (toast = ''), 1800);
	}
</script>

{#if selected.size}
	<div class="bar" role="toolbar" aria-label={ta ? 'வசனச் செயல்கள்' : 'Verse actions'}>
		<span class="label">{label}</span>
		<button type="button" onclick={copy}>{ta ? 'நகல்' : 'Copy'}</button>
		<button type="button" onclick={share}>{ta ? 'பகிர்' : 'Share'}</button>
		<button type="button" class="ghost" onclick={onclear} aria-label={ta ? 'தெரிவை நீக்கு' : 'Clear selection'}>×</button>
		{#if toast}<span class="toast" role="status">{toast}</span>{/if}
	</div>
{/if}

<style>
	.bar { position: fixed; left: 50%; bottom: max(1rem, env(safe-area-inset-bottom)); transform: translateX(-50%); z-index: 15; display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.6rem 0.5rem 0.9rem; background: var(--surface); border: 1px solid var(--line); border-radius: 999px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18); max-width: calc(100vw - 2rem); }
	.label { font-family: var(--tamil); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 40vw; }
	button { border: 1px solid var(--line); background: var(--surface-2); color: inherit; border-radius: 999px; padding: 0.4rem 0.9rem; min-height: 40px; cursor: pointer; font-family: var(--tamil); }
	button:hover { border-color: var(--accent); }
	.ghost { background: none; border-color: transparent; font-size: 1.3rem; line-height: 1; min-width: 40px; padding: 0; color: var(--muted); }
	.toast { position: absolute; bottom: calc(100% + 0.5rem); left: 50%; transform: translateX(-50%); background: var(--ink); color: var(--bg); font-size: 0.85rem; padding: 0.35rem 0.7rem; border-radius: 6px; white-space: nowrap; }
</style>

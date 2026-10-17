<script lang="ts">
	// Hover preview for verse links anywhere on the site: rest the mouse on a
	// reference such as "1 பேது 1:5" for half a second and the verse appears
	// underneath it. On touch, where there is no hover, a tap opens the same
	// preview instead of leaving the page; tapping the preview (or the link
	// again) goes to the verse, tapping anywhere else closes it.
	// Lists that already print the verse text opt out with data-no-preview.
	import { afterNavigate } from '$app/navigation';
	import { bookNameIn, findBook, findVersion } from '$lib/content/manifest';
	import { chapterCached, versesText } from '$lib/content/verses';
	import type { ChapterJson } from '$lib/content/types';

	const DELAY = 500;
	const MAX = 420;

	let preview = $state<{ href: string; label: string; text: string; lang: string; top: number; left: number; above: boolean } | null>(null);
	let pinned = $state(false);
	let box = $state<HTMLAnchorElement | null>(null);
	let link: HTMLAnchorElement | null = null;
	let timer = 0;
	let touch = false;

	/** `/irvtam/john/3/16`, `/irvtam/john/3.16` or `/irvtam+bsb/john/3/16-18` → what to show; null for any other link. */
	function parse(a: HTMLAnchorElement) {
		if (a.origin !== location.origin) return null;
		const m = a.pathname.match(/^\/([a-z0-9+]+)\/([^/]+)\/(\d+)[/.](\d+)(?:-(\d+))?\/?$/i);
		if (!m) return null;
		const version = findVersion(m[1].split('+')[0]);
		const book = findBook(decodeURIComponent(m[2]));
		if (!version || !book) return null;
		const start = Number(m[4]);
		return { version, book, chapter: Number(m[3]), start, end: m[5] ? Number(m[5]) : start };
	}

	async function show(a: HTMLAnchorElement) {
		const ref = parse(a);
		if (!ref) return;
		let ch: ChapterJson;
		try {
			ch = await chapterCached(fetch, ref.version.code, ref.book.code, ref.chapter);
		} catch {
			return;
		}
		if (link !== a) return; // the mouse moved on while the chapter loaded
		let text = versesText(ch, ref.start, ref.end);
		if (!text) return;
		if (text.length > MAX) text = text.slice(0, MAX).replace(/\s\S*$/, '') + ' …';
		const name = bookNameIn(ref.book, ref.version);
		const verses = ref.end > ref.start ? `${ref.start}-${ref.end}` : `${ref.start}`;
		const r = a.getBoundingClientRect();
		const width = Math.min(360, innerWidth - 16);
		// Below the link, as asked; above it only when there is no room below.
		const above = r.bottom + 180 > innerHeight && r.top > 200;
		preview = {
			href: a.href,
			label: `${name} ${ref.chapter}:${verses} · ${ref.version.short}`,
			text,
			lang: ref.version.lang,
			top: above ? r.top - 8 : r.bottom + 8,
			left: Math.max(8, Math.min(r.left, innerWidth - width - 8)),
			above
		};
	}

	function hide() {
		clearTimeout(timer);
		link = null;
		preview = null;
		pinned = false;
	}

	function onOver(e: PointerEvent) {
		if (e.pointerType !== 'mouse' || pinned) return;
		const a = (e.target as Element | null)?.closest?.('a[href]') as HTMLAnchorElement | null;
		if (!a || a === link) return;
		hide();
		if (a.closest('[data-no-preview]') || !parse(a)) return;
		link = a;
		timer = window.setTimeout(() => show(a), DELAY);
	}
	function onOut(e: PointerEvent) {
		if (!link || pinned) return;
		const to = e.relatedTarget as Node | null;
		if (to && link.contains(to)) return;
		hide();
	}
	function onDown(e: PointerEvent) {
		touch = e.pointerType !== 'mouse';
		const t = e.target as Node | null;
		// Leave an open preview alone when the tap is on it or on its own link:
		// both go on to the verse.
		if (pinned && t && (box?.contains(t) || link?.contains(t))) return;
		hide();
	}
	/** Capture phase, so the tap is caught before the router follows the link. */
	function onClick(e: MouseEvent) {
		if (!touch || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		const a = (e.target as Element | null)?.closest?.('a[href]') as HTMLAnchorElement | null;
		if (!a || a === box || (pinned && a === link)) return;
		if (a.closest('[data-no-preview]') || !parse(a)) return;
		e.preventDefault();
		hide();
		link = a;
		pinned = true;
		show(a);
	}

	afterNavigate(hide);
</script>

<svelte:document onpointerover={onOver} onpointerout={onOut} onpointerdown={onDown} onclickcapture={onClick} />
<svelte:window onscroll={hide} onblur={hide} onkeydown={(e) => e.key === 'Escape' && hide()} />

{#if preview}
	<a
		bind:this={box}
		class="preview"
		class:above={preview.above}
		class:pinned
		href={preview.href}
		role={pinned ? undefined : 'tooltip'}
		tabindex={pinned ? undefined : -1}
		style="top: {preview.top}px; left: {preview.left}px"
	>
		<span class="label">{preview.label}{#if pinned}<span class="go" aria-hidden="true"> →</span>{/if}</span>
		<span class="text" lang={preview.lang}>{preview.text}</span>
	</a>
{/if}

<style>
	.preview { position: fixed; z-index: 40; display: block; width: min(360px, calc(100vw - 16px)); padding: 0.8rem 0.95rem 0.9rem; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: var(--r-l); box-shadow: var(--shadow); color: inherit; text-decoration: none; pointer-events: none; animation: rise 0.12s ease-out; }
	.preview.pinned { pointer-events: auto; cursor: pointer; -webkit-tap-highlight-color: transparent; }
	.preview.pinned:active { background: var(--surface-2, var(--surface)); }
	.preview.above { transform: translateY(-100%); }
	.label { display: block; margin: 0 0 0.35rem; font-family: var(--tamil); font-size: 0.8rem; font-weight: 700; color: var(--accent); }
	.text { display: block; margin: 0; font-size: 0.98rem; line-height: 1.7; color: var(--ink); }
	.text[lang='ta'] { font-family: var(--tamil); font-size: 1.05rem; line-height: 1.8; }
	.text[lang='en'] { font-family: var(--en); color: var(--ink-en); }
	@keyframes rise { from { opacity: 0; } to { opacity: 1; } }
	@media (prefers-reduced-motion: reduce) { .preview { animation: none; } }
</style>

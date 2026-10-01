<script lang="ts">
	// A drag handle on the inner edge of a wide-screen side column (the book
	// rail or the context panel). Dragging sets the column's width on <html>
	// live and saves it on release; arrow keys step it, and a double-click or
	// Home returns the column to its automatic width.
	import { columnWidth, settings } from '$lib/settings/store.svelte';

	let {
		side,
		lang
	}: {
		/** Which column the grip resizes: the rail grows rightwards, the panel leftwards. */
		side: 'rail' | 'panel';
		lang: 'ta' | 'en';
	} = $props();

	const ta = $derived(lang === 'ta');
	const prop = $derived(side === 'rail' ? '--rail-w' : '--panel-w');
	const key = $derived(side === 'rail' ? 'railWidth' : 'panelWidth');
	const [lo, hi] = $derived(side === 'rail' ? [200, 520] : [300, 720]);
	/** The reading column keeps at least this much room. */
	const READING_MIN = 480;

	let grip: HTMLDivElement | undefined = $state();
	let width = $state(0);
	let drag: { x: number; w: number; other: number } | null = null;

	function column() {
		return grip?.closest<HTMLElement>('aside');
	}
	function otherColumn() {
		return document.querySelector<HTMLElement>(side === 'rail' ? '.reader aside.panel' : '.reader aside.rail');
	}
	function clamp(w: number, other: number) {
		// The grid also caps each side column at 40% of the window (ChapterPage).
		const page = document.documentElement.clientWidth; // without the scrollbar
		const room = Math.min(page - other - READING_MIN, innerWidth * 0.4);
		return Math.round(Math.max(lo, Math.min(hi, room, w)));
	}
	function set(w: number) {
		width = w;
		columnWidth(prop, w);
	}
	function save(w: number) {
		settings.update({ [key]: w });
	}

	function down(e: PointerEvent) {
		if (e.button !== 0) return;
		const col = column();
		if (!col) return;
		e.preventDefault();
		grip?.setPointerCapture(e.pointerId);
		drag = { x: e.clientX, w: col.getBoundingClientRect().width, other: otherColumn()?.getBoundingClientRect().width ?? 0 };
		document.documentElement.classList.add('col-resizing');
	}
	function move(e: PointerEvent) {
		if (!drag) return;
		const dx = e.clientX - drag.x;
		set(clamp(side === 'rail' ? drag.w + dx : drag.w - dx, drag.other));
	}
	function up() {
		if (!drag) return;
		drag = null;
		document.documentElement.classList.remove('col-resizing');
		if (width) save(width);
	}
	function reset() {
		width = 0;
		save(0);
	}
	function onKey(e: KeyboardEvent) {
		const col = column();
		if (!col) return;
		const step = e.shiftKey ? 64 : 16;
		// Left/right move the column's inner edge, as a drag would.
		const grow = side === 'rail' ? { ArrowRight: step, ArrowLeft: -step } : { ArrowLeft: step, ArrowRight: -step };
		if (e.key === 'Home') {
			e.preventDefault();
			reset();
			return;
		}
		const d = grow[e.key as keyof typeof grow];
		if (!d) return;
		// The reader turns the chapter on ←/→; these arrows are the grip's.
		e.preventDefault();
		e.stopPropagation();
		const w = clamp(col.getBoundingClientRect().width + d, otherColumn()?.getBoundingClientRect().width ?? 0);
		set(w);
		save(w);
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -- a focusable separator is the ARIA pattern for a resize handle -->
<div
	bind:this={grip}
	class="grip {side}"
	role="separator"
	aria-orientation="vertical"
	aria-label={side === 'rail' ? (ta ? 'புத்தகப் பட்டியலின் அகலம்' : 'Book list width') : ta ? 'பக்கப் பலகையின் அகலம்' : 'Side panel width'}
	aria-valuemin={lo}
	aria-valuemax={hi}
	aria-valuenow={width || settings.value[key] || undefined}
	title={ta ? 'அகலத்தை மாற்ற இழுக்கவும் · இருமுறை சொடுக்கினால் இயல்பு அகலம்' : 'Drag to resize · double-click to reset'}
	tabindex="0"
	onpointerdown={down}
	onpointermove={move}
	onpointerup={up}
	onpointercancel={up}
	ondblclick={reset}
	onkeydown={onKey}
></div>

<style>
	/* A 9px hit area centred on the column's border; the line shows on hover and while dragging. */
	.grip { position: absolute; top: 0; bottom: 0; width: 9px; z-index: 3; cursor: col-resize; touch-action: none; }
	.grip.rail { right: -5px; }
	.grip.panel { left: -5px; }
	.grip::after { content: ''; position: absolute; top: 0; bottom: 0; left: 3px; width: 3px; border-radius: 3px; background: var(--accent); opacity: 0; transition: opacity 0.12s; }
	.grip:hover::after, .grip:focus-visible::after, :global(html.col-resizing) .grip::after { opacity: 0.7; }
	.grip:focus-visible { outline: none; }
	/* While dragging, the whole page shows the resize cursor and no text gets selected. */
	:global(html.col-resizing), :global(html.col-resizing *) { cursor: col-resize !important; user-select: none !important; }
</style>

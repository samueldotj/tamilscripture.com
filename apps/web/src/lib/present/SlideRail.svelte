<script lang="ts">
	// The left rail of the editor (design 11A): the presentation's name, its
	// slides as small cards in order, and "new slide". Cards drag to reorder.
	import { plainText } from '$lib/md/parse';
	import { verseLabel, type Slide } from './types';

	let {
		slides,
		current,
		lang = 'ta',
		onselect,
		onadd,
		onmove
	}: {
		slides: Slide[];
		current: number;
		lang?: 'ta' | 'en';
		onselect: (i: number) => void;
		onadd: () => void;
		onmove: (from: number, to: number) => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	let dragging = $state<number | null>(null);
	let over = $state<number | null>(null);

	function onDragStart(e: DragEvent, i: number) {
		dragging = i;
		e.dataTransfer?.setData('text/plain', String(i));
		if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
	}
	function onDragOver(e: DragEvent, i: number) {
		if (dragging === null) return;
		e.preventDefault();
		over = i;
	}
	function onDrop(e: DragEvent, i: number) {
		e.preventDefault();
		if (dragging !== null && dragging !== i) onmove(dragging, i);
		dragging = over = null;
	}
	function onKey(e: KeyboardEvent, i: number) {
		// Alt+↑ / Alt+↓ move a slide without a mouse.
		if (e.altKey && e.key === 'ArrowUp' && i > 0) { e.preventDefault(); onmove(i, i - 1); }
		else if (e.altKey && e.key === 'ArrowDown' && i < slides.length - 1) { e.preventDefault(); onmove(i, i + 1); }
	}
	/** Bars stand in for the notes on a thumbnail: one per line, up to three. */
	function bars(s: Slide): number[] {
		const n = s.notes.split('\n').filter((l) => l.trim()).length;
		return [100, 82, 60].slice(0, Math.min(3, n));
	}
</script>

<ol class="rail" aria-label={ta ? 'ஸ்லைடுகள்' : 'Slides'}>
	{#each slides as s, i (s.id)}
		<li class:current={i === current} class:over={over === i && dragging !== i} class:dragging={dragging === i}
			draggable="true"
			ondragstart={(e) => onDragStart(e, i)}
			ondragover={(e) => onDragOver(e, i)}
			ondragleave={() => (over === i ? (over = null) : null)}
			ondrop={(e) => onDrop(e, i)}
			ondragend={() => (dragging = over = null)}>
			<button type="button" aria-current={i === current ? 'true' : undefined} aria-label={`${ta ? 'ஸ்லைடு' : 'Slide'} ${i + 1}`} onclick={() => onselect(i)} onkeydown={(e) => onKey(e, i)}>
				<span class="n">{i + 1}</span>
				<span class="thumb">
					{#if s.title?.trim() && !s.verses.length}
						<span class="title" lang={/[஀-௿]/.test(s.title) ? 'ta' : 'en'}>{s.title.trim()}</span>
					{:else if s.verses.length}
						<span class="ref" lang="ta">{verseLabel(s.verses[0], lang)}{s.verses.length > 1 ? ` +${s.verses.length - 1}` : ''}</span>
						{#each bars(s) as w, j (j)}<span class="bar" style="width: {w}%"></span>{/each}
					{:else if s.notes.trim()}
						<span class="note">{plainText(s.notes, 60)}</span>
					{:else}
						<span class="note muted">{ta ? 'வெற்று' : 'Empty'}</span>
					{/if}
				</span>
			</button>
		</li>
	{/each}
	<!-- Every presentation ends with this slide; it is not stored and not editable. -->
	<li class="closing">
		<span class="n">{slides.length + 1}</span>
		<span class="thumb"><span class="title" lang="ta">நன்றி · 👍 👎</span><span class="note muted">{ta ? 'வாக்கு · பகிர்' : 'votes · share'}</span></span>
	</li>
</ol>
<button type="button" class="chip dashed add" onclick={onadd}>+ <span lang={ta ? 'ta' : 'en'}>{ta ? 'புதிய ஸ்லைடு' : 'New slide'}</span></button>

<style>
	.rail { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
	li { border-radius: 12px; border: var(--bw) solid var(--line); }
	li.current { border-color: var(--accent); background: var(--surface); }
	li.over { border-color: var(--accent); border-style: dashed; }
	li.dragging { opacity: 0.5; }
	li.closing { display: flex; gap: 10px; padding: 8px; border-style: dashed; opacity: 0.8; }
	li.closing .thumb { text-align: center; }
	li button { display: flex; gap: 10px; align-items: stretch; width: 100%; padding: 8px; border: 0; background: none; color: inherit; cursor: pointer; text-align: left; border-radius: 12px; }
	li button:hover .thumb { outline: 1px solid var(--line-2); }
	.n { width: 18px; font-size: 0.75rem; font-weight: 700; color: var(--muted); display: flex; align-items: center; justify-content: center; flex: none; }
	li.current .n { color: var(--accent); }
	.thumb { flex: 1; min-width: 0; min-height: 64px; border-radius: 8px; background: #0E1015; display: flex; flex-direction: column; justify-content: center; gap: 4px; padding: 10px 12px; color: #F1ECE1; }
	.title { font-family: var(--tamil); font-size: 0.9rem; font-weight: 600; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.ref { font-size: 0.55rem; letter-spacing: 0.1em; color: #D9B25C; font-weight: 700; font-family: var(--tamil); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.bar { height: 4px; border-radius: 2px; background: #3D4554; }
	.note { font-size: 0.62rem; color: #C4BEB1; font-family: var(--tamil); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; }
	.muted { color: #7E8798; }
	.add { width: 100%; min-height: 48px; margin-top: 8px; }
	.add [lang='ta'] { font-family: var(--tamil); }
</style>

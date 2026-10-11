<script lang="ts">
	// The psalter tune on the Psalms explorer's card (design: Psalms Explorer v2,
	// "Psalter tune"; docs/feature_psalms_explorer.md §8). Notation and audio are
	// rendered at build time by tools/psalter; this plays the MP3 and lights the
	// note that is sounding, from events.json. "Full tune" swaps the first line
	// for the whole melody.
	import { onDestroy, onMount } from 'svelte';
	import { contentUrl } from '$lib/content/manifest';
	import type { Tune } from './types';

	let { tune, ta }: { tune: Tune; ta: boolean } = $props();

	interface Events {
		duration: number;
		incipit_notes: number;
		/** [x, y, id]: the notehead as fractions of the drawing, and its SVG id */
		notes: { on: number; off: number; midi: number; full: [number, number, string]; incipit?: [number, number, string] }[];
	}

	const base = $derived(`entities/psalter/${tune.id}`);
	let svgs = $state<{ incipit: string; full: string } | null>(null);
	let events = $state<Events | null>(null);
	let full = $state(false);
	let playing = $state(false);
	let now = $state(0);
	let box = $state<HTMLElement>();
	let audio: HTMLAudioElement | null = null;
	let frame = 0;
	let lit: Element | null = null;

	onMount(async () => {
		const get = (f: string) => fetch(contentUrl(`${base}/${f}`));
		const [i, f, e] = await Promise.all([get('incipit.svg'), get('full.svg'), get('events.json')]);
		if (i.ok && f.ok && e.ok) {
			svgs = { incipit: await i.text(), full: await f.text() };
			events = await e.json();
		}
	});
	onDestroy(() => {
		cancelAnimationFrame(frame);
		audio?.pause();
	});

	const fmt = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, '0')}`;
	const total = $derived(events?.duration ?? 0);

	/** Light the note sounding at `ms` in the drawing on show. */
	function light(ms: number) {
		if (!events || !box) return;
		const n = events.notes.find((x) => x.on <= ms && ms < x.off);
		const id = n ? (full ? n.full[2] : n.incipit?.[2]) : undefined;
		const el = id ? box.querySelector(`[id="${id}"]`) : null;
		if (el === lit) return;
		lit?.classList.remove('on');
		el?.classList.add('on');
		lit = el;
	}

	function tick() {
		if (!audio) return;
		now = audio.currentTime * 1000;
		light(now);
		if (playing) frame = requestAnimationFrame(tick);
	}

	function toggle() {
		if (!audio) {
			audio = new Audio(contentUrl(`${base}/audio.mp3`));
			audio.addEventListener('ended', () => {
				playing = false;
				now = 0;
				light(-1);
			});
			audio.addEventListener('pause', () => (playing = false));
		}
		if (playing) {
			audio.pause();
		} else {
			audio.play().then(() => {
				playing = true;
				frame = requestAnimationFrame(tick);
			}).catch(() => (playing = false));
		}
	}

	$effect(() => {
		// Swapping drawings drops the lit note; light it again in the new one.
		void full;
		lit = null;
		queueMicrotask(() => light(now));
	});
</script>

<div class="tune">
	<span class="kicker">{ta ? 'சங்கீதப் பண்' : 'Psalter tune'} · {tune.name}</span>
	<div class="panel">
		{#if svgs}
			<!-- Build output of tools/psalter (Verovio), not user content. -->
			<div class="score" class:full bind:this={box} role="img" aria-label="{ta ? 'இசைக் குறியீடு' : 'Musical notation for'} {tune.name}">{@html full ? svgs.full : svgs.incipit}</div>
		{:else}
			<div class="score empty" aria-busy="true"></div>
		{/if}
		<div class="controls">
			<button type="button" class="play" onclick={toggle} aria-label={playing ? (ta ? 'இடைநிறுத்து' : 'Pause') : (ta ? 'இசை' : 'Play')} aria-pressed={playing} disabled={!events}>
				{#if playing}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
				{:else}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5z" /></svg>
				{/if}
			</button>
			<div class="meta">
				<div class="row"><span>{tune.meter} · {tune.key}</span><span class="time">{fmt(now)} / {fmt(total)}</span></div>
				<div class="bar"><div style="width: {total ? Math.min(100, (now / total) * 100) : 0}%"></div></div>
			</div>
		</div>
		<div class="foot">
			<span>{tune.source}{tune.composer && tune.composer !== 'Anonymous' ? ` · ${tune.composer}` : ''}</span>
			<button type="button" class="more" onclick={() => (full = !full)} aria-expanded={full}>{full ? (ta ? 'முதல் வரி' : 'First line') : (ta ? 'முழுப் பண்' : 'Full tune')}</button>
		</div>
	</div>
</div>

<style>
	.tune { display: flex; flex-direction: column; gap: 0.5rem; }
	.kicker { display: block; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
	.panel { background: var(--surface); border: var(--bw) solid var(--line); border-radius: var(--r); padding: 0.75rem 0.9rem; display: flex; flex-direction: column; gap: 0.6rem; }
	.score { color: var(--ink); }
	.score :global(svg) { display: block; width: 100%; height: auto; max-height: 110px; }
	.score.full :global(svg) { max-height: none; }
	.score.empty { height: 64px; }
	.score :global(g.note.on) { color: var(--accent); }
	.controls { display: flex; align-items: center; gap: 0.7rem; }
	.play { width: 44px; height: 44px; border-radius: 999px; border: var(--bw) solid var(--accent); background: var(--accent); color: var(--on-accent); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; flex: none; }
	.play:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
	.play:disabled { opacity: 0.5; cursor: default; }
	.meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.35rem; }
	.row { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.78rem; color: var(--muted); }
	.time { font-variant-numeric: tabular-nums; }
	.bar { height: 4px; border-radius: 999px; background: var(--line); overflow: hidden; }
	.bar div { height: 100%; background: var(--accent); }
	.foot { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; font-size: 0.74rem; color: var(--muted); }
	.more { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; padding: 0.2rem 0; text-decoration: underline; text-underline-offset: 3px; white-space: nowrap; }
</style>

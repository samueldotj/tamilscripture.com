<script lang="ts">
	// The psalter tune on the Psalms explorer's card (design: Psalms Explorer v2,
	// "Psalter tune"; docs/feature_psalms_explorer.md §8). Notation and audio are
	// rendered at build time by tools/psalter; this plays the MP3 (one stanza on
	// organ) once for each of `stanzas`, a breath between, at the tempo chosen, and
	// lights the note that is sounding, from events.json. The words of the stanza being
	// sung are written under the notes, and the stanza and line sung are reported
	// through `onplace`. "Full tune" swaps the first line for the whole melody.
	import { onDestroy, onMount } from 'svelte';
	import { contentUrl } from '$lib/content/manifest';
	import { stanzaOnNotes } from './lyrics';
	import type { Tune } from './types';

	let { tune, ta, stanzas = 1, lyrics, onplace }: {
		tune: Tune;
		ta: boolean;
		/** How many times to play the tune: the stanzas of the version being sung. */
		stanzas?: number;
		/** The version's words as syllables (stanza → line → syllable), written under the notes. */
		lyrics?: string[][][];
		/** The stanza and line being sung, or null when stopped or between stanzas. */
		onplace?: (place: { stanza: number; line: number } | null) => void;
	} = $props();

	/** [x, y, id, lyric baseline]: the notehead and the words' baseline as fractions of the drawing, and its SVG id */
	type Head = [number, number, string, number | null];
	interface Events {
		duration: number;
		bpm: number;
		incipit_notes: number;
		/** When each line of a stanza starts (ms) */
		lines: number[];
		/** Per line, the notes that start a syllable */
		slots: number[][];
		notes: { on: number; off: number; midi: number; full: Head; incipit?: Head }[];
	}

	/** Slower, as written, faster: the playback rate, pitch kept. */
	const TEMPI = [0.85, 1, 1.15];

	const base = $derived(`entities/psalter/${tune.id}`);
	let svgs = $state<{ incipit: string; full: string } | null>(null);
	let events = $state<Events | null>(null);
	let full = $state(false);
	let playing = $state(false);
	let now = $state(0);
	let box = $state<HTMLElement>();
	let stanza = $state(0);
	let rate = $state(1);
	let audio: HTMLAudioElement | null = null;
	let frame = 0;
	let lit: Element[] = [];

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
		onplace?.(null);
	});

	const fmt = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, '0')}`;
	/** Where the melody comes from, and the other names it goes by. */
	const credit = $derived(
		[
			tune.source,
			tune.composer && tune.composer !== 'Anonymous' ? tune.composer : '',
			tune.other_names?.length ? (ta ? 'வேறு பெயர்: ' : 'also known as ') + tune.other_names.join(', ') : ''
		].filter(Boolean).join(' · ')
	);
	const once = $derived(events?.duration ?? 0);
	/** A breath between stanzas, about a beat, as a congregation takes. */
	const breath = 700;
	// Times in the audio's own clock, shown in the listener's: divided by the rate.
	const total = $derived((stanzas * once + (stanzas - 1) * breath) / rate);
	const elapsed = $derived((stanza * (once + breath) + Math.min(now, once + breath)) / rate);

	/** The stanza's words on the notes, and for each note the syllable it sounds. */
	const words = $derived(events && lyrics?.[stanza] ? stanzaOnNotes(lyrics[stanza], events.slots) : new Map<number, string>());
	const owner = $derived.by(() => {
		const out: number[] = [];
		let cur = -1;
		events?.notes.forEach((_, i) => {
			if (words.has(i)) cur = i;
			out.push(cur);
		});
		return out;
	});

	/** Writes the words into the drawing on show, under their notes, in its own units. */
	function write() {
		const svg = box?.querySelector('svg.definition-scale') as SVGSVGElement | null;
		if (!svg || !events) return;
		svg.querySelector('g.words')?.remove();
		if (!words.size) return;
		const [, , w, h] = svg.getAttribute('viewBox')!.split(' ').map(Number);
		const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
		g.setAttribute('class', 'words');
		for (const [i, text] of words) {
			const head = full ? events.notes[i]?.full : events.notes[i]?.incipit;
			if (!head || head[3] == null) continue;
			const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
			t.setAttribute('x', String(head[0] * w + 80));
			t.setAttribute('y', String(head[3] * h));
			t.setAttribute('text-anchor', 'middle');
			t.setAttribute('font-size', '300');
			t.setAttribute('data-n', String(i));
			t.textContent = text;
			g.appendChild(t);
		}
		svg.appendChild(g);
	}

	/** Light the note sounding at `ms` and its syllable in the drawing on show. */
	function light(ms: number) {
		if (!events || !box) return;
		const i = events.notes.findIndex((x) => x.on <= ms && ms < x.off);
		const n = events.notes[i];
		const id = n ? (full ? n.full[2] : n.incipit?.[2]) : undefined;
		const els = [id ? box.querySelector(`[id="${id}"]`) : null, i >= 0 && owner[i] >= 0 ? box.querySelector(`text[data-n="${owner[i]}"]`) : null].filter((e): e is Element => !!e);
		if (els.length === lit.length && els.every((e, k) => e === lit[k])) return;
		lit.forEach((e) => e.classList.remove('on'));
		els.forEach((e) => e.classList.add('on'));
		lit = els;
	}

	let place: string | null = null;
	function report(ms: number) {
		const line = events && ms < once ? events.lines.findLastIndex((t) => t <= ms) : -1;
		const key = line < 0 ? null : `${stanza}.${line}`;
		if (key === place) return;
		place = key;
		onplace?.(line < 0 ? null : { stanza, line });
	}

	function tick() {
		if (!audio) return;
		now = audio.currentTime * 1000;
		// The stanza is sung; after the breath, the next one starts (the organ's tail is cut).
		if (now >= once + breath && stanza + 1 < stanzas) {
			stanza += 1;
			audio.currentTime = 0;
			now = 0;
		}
		light(now);
		report(now);
		if (playing) frame = requestAnimationFrame(tick);
	}

	function stop() {
		playing = false;
		now = 0;
		stanza = 0;
		light(-1);
		report(-1);
	}

	function toggle() {
		if (!audio) {
			audio = new Audio(contentUrl(`${base}/audio.mp3`));
			audio.preservesPitch = true;
			audio.addEventListener('ended', stop);
			audio.addEventListener('pause', () => (playing = false));
		}
		audio.playbackRate = rate;
		if (playing) {
			audio.pause();
		} else {
			audio.play().then(() => {
				playing = true;
				frame = requestAnimationFrame(tick);
			}).catch(() => (playing = false));
		}
	}

	function setRate(r: number) {
		rate = r;
		if (audio) audio.playbackRate = r;
	}

	$effect(() => {
		// A new drawing, stanza or tune: write the words again and relight the note.
		void full;
		void words;
		void svgs;
		lit = [];
		queueMicrotask(() => {
			write();
			light(playing || now > 0 ? now : -1);
		});
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
				<div class="row"><span>{tune.meter} · {tune.key}{#if stanzas > 1}{' · '}{ta ? `பத்தி ${stanza + 1}/${stanzas}` : `stanza ${stanza + 1} of ${stanzas}`}{/if}</span><span class="time">{fmt(elapsed)} / {fmt(total)}</span></div>
				<div class="bar"><div style="width: {total ? Math.min(100, (elapsed / total) * 100) : 0}%"></div></div>
			</div>
		</div>
		{#if events}
			<div class="tempo" role="group" aria-label={ta ? 'வேகம்' : 'Tempo'}>
				<span class="lbl">{ta ? 'வேகம்' : 'Tempo'}</span>
				{#each TEMPI as r (r)}
					<button type="button" class:on={r === rate} aria-pressed={r === rate} onclick={() => setRate(r)}>
						{r < 1 ? (ta ? 'மெதுவாக' : 'Slower') : r > 1 ? (ta ? 'வேகமாக' : 'Faster') : ta ? 'இயல்பு' : 'Normal'}
						<span class="bpm">♩ = {Math.round(events.bpm * r)}</span>
					</button>
				{/each}
			</div>
		{/if}
		<div class="foot">
			<span>{credit}</span>
			<button type="button" class="more" onclick={() => (full = !full)} aria-expanded={full}>{full ? (ta ? 'முதல் வரி' : 'First line') : (ta ? 'முழுப் பண்' : 'Full tune')}</button>
		</div>
	</div>
</div>

<style>
	.tune { display: flex; flex-direction: column; gap: 0.5rem; }
	.kicker { display: block; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
	.panel { background: var(--surface); border: var(--bw) solid var(--line); border-radius: var(--r); padding: 0.75rem 0.9rem; display: flex; flex-direction: column; gap: 0.6rem; }
	.score { color: var(--ink); }
	.score :global(svg) { display: block; width: 100%; height: auto; max-height: 140px; }
	.score.full :global(svg) { max-height: none; }
	.score.empty { height: 64px; }
	.score :global(g.note.on) { color: var(--accent); }
	.score :global(g.words text) { font-family: var(--sans); fill: var(--ink-2); }
	.score :global(g.words text.on) { fill: var(--accent); font-weight: 700; }
	.controls { display: flex; align-items: center; gap: 0.7rem; }
	.play { width: 44px; height: 44px; border-radius: 999px; border: var(--bw) solid var(--accent); background: var(--accent); color: var(--on-accent); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; flex: none; }
	.play:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
	.play:disabled { opacity: 0.5; cursor: default; }
	.meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.35rem; }
	.row { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.78rem; color: var(--muted); }
	.time { font-variant-numeric: tabular-nums; }
	.bar { height: 4px; border-radius: 999px; background: var(--line); overflow: hidden; }
	.bar div { height: 100%; background: var(--accent); }
	.tempo { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; }
	.tempo .lbl { font-size: 0.74rem; color: var(--muted); margin-right: 0.2rem; }
	.tempo button { display: inline-flex; align-items: baseline; gap: 0.35rem; min-height: 32px; padding: 0.2rem 0.65rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font: inherit; font-size: 0.78rem; font-weight: 600; cursor: pointer; }
	.tempo button:hover { border-color: var(--accent); }
	.tempo button.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.tempo .bpm { font-weight: 400; font-size: 0.72rem; opacity: 0.8; font-variant-numeric: tabular-nums; }
	.foot { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; font-size: 0.74rem; color: var(--muted); }
	.more { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; padding: 0.2rem 0; text-decoration: underline; text-underline-offset: 3px; white-space: nowrap; }
</style>

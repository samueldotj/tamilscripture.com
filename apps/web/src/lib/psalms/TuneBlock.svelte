<script lang="ts">
	// The psalter tune on the Psalms explorer's card (design: Psalms Explorer v2,
	// "Psalter tune"; docs/feature_psalms_explorer.md §8). Notation and audio are
	// rendered at build time by tools/psalter; this plays the MP3 (one stanza on
	// organ) once for each of `stanzas`, a breath between, at the tempo chosen, and
	// lights the note that is sounding, from events.json. The words of the stanza being
	// sung are written under the notes, and the stanza and line sung are reported
	// through `onplace`. "Full tune" swaps the first line for the whole melody;
	// "Full screen" shows the whole tune and its words as large as the screen allows,
	// for singing from, and keeps the screen awake meanwhile. A tap on a note or a word
	// sings from there; the timeline can be dragged, or stepped with the arrow keys.
	import { onDestroy, onMount } from 'svelte';
	import { contentUrl } from '$lib/content/manifest';
	import { stanzaOnNotes } from './lyrics';
	import { nearestNote, place as placeAt } from './seek';
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
	/** Full screen for singing: the panel fills the screen (the Fullscreen API where there
	 *  is one, else a fixed overlay, as on iPhone). */
	let big = $state(false);
	let panel = $state<HTMLElement>();
	let fullBefore = false;
	let wake: { release(): Promise<void> } | null = null;

	async function enterBig() {
		fullBefore = full;
		followed = null;
		full = true;
		big = true;
		try {
			await panel?.requestFullscreen?.();
		} catch {
			// No element full screen here: the overlay alone covers the page.
		}
		try {
			wake = (await (navigator as Navigator & { wakeLock?: { request(t: 'screen'): Promise<{ release(): Promise<void> }> } }).wakeLock?.request('screen')) ?? null;
		} catch {
			wake = null;
		}
	}

	function exitBig() {
		if (!big) return;
		big = false;
		full = fullBefore;
		if (document.fullscreenElement === panel) document.exitFullscreen().catch(() => {});
		wake?.release().catch(() => {});
		wake = null;
	}

	onMount(() => {
		const change = () => {
			if (big && !document.fullscreenElement && wasFull) exitBig();
			wasFull = !!document.fullscreenElement;
		};
		let wasFull = false;
		const key = (e: KeyboardEvent) => {
			if (e.key === 'Escape' && big) exitBig();
		};
		document.addEventListener('fullscreenchange', change);
		document.addEventListener('keydown', key);
		return () => {
			document.removeEventListener('fullscreenchange', change);
			document.removeEventListener('keydown', key);
		};
	});
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
		exitBig();
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
		if (big && els[0]) follow(els[0]);
	}

	/** Full screen: keep the line being sung in view, with its words, scrolling as it moves on. */
	let followed: Element | null = null;
	function follow(note: Element) {
		const system = note.closest('g.system');
		if (!system || system === followed || !box) return;
		followed = system;
		const r = system.getBoundingClientRect();
		const view = box.getBoundingClientRect();
		const bottom = r.bottom + r.height * 0.4; // the words under the staff
		if (r.top >= view.top && bottom <= view.bottom) return;
		box.scrollBy({ top: r.top - view.top - 8, behavior: 'smooth' });
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

	function load(): HTMLAudioElement {
		if (!audio) {
			audio = new Audio(contentUrl(`${base}/audio.mp3`));
			audio.preservesPitch = true;
			audio.addEventListener('ended', stop);
			audio.addEventListener('pause', () => (playing = false));
		}
		audio.playbackRate = rate;
		return audio;
	}

	function play() {
		load().play().then(() => {
			playing = true;
			cancelAnimationFrame(frame);
			frame = requestAnimationFrame(tick);
		}).catch(() => (playing = false));
	}

	function toggle() {
		if (playing) audio?.pause();
		else play();
	}

	/** Go to `ms` of the whole psalm in the audio's own clock (stanzas a breath apart). */
	function seek(ms: number) {
		const p = placeAt(ms, once, breath, stanzas);
		stanza = p.stanza;
		now = p.at;
		load().currentTime = p.at / 1000;
		light(now);
		report(now);
	}

	/** A tap on the score: sing from the note tapped, or from the note of the word tapped. */
	function tapScore(e: MouseEvent) {
		const svg = box?.querySelector('svg.definition-scale') as SVGSVGElement | null;
		const m = svg?.getScreenCTM();
		if (!svg || !m || !events) return;
		const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
		const [, , w, h] = svg.getAttribute('viewBox')!.split(' ').map(Number);
		const i = nearestNote(events.notes.map((n) => (full ? n.full : n.incipit)), pt.x, pt.y, w, h);
		if (i < 0) return;
		seek(stanza * (once + breath) + events.notes[i].on);
		if (!playing) play();
	}

	/** The timeline: a press or drag goes to that point of the psalm. */
	let bar = $state<HTMLElement>();
	function barAt(e: PointerEvent) {
		const r = bar!.getBoundingClientRect();
		const f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
		seek(f * total * rate);
	}
	function barDown(e: PointerEvent) {
		if (!events) return;
		bar!.setPointerCapture(e.pointerId);
		barAt(e);
	}
	function barMove(e: PointerEvent) {
		if (bar?.hasPointerCapture(e.pointerId)) barAt(e);
	}
	/** Arrow keys step five seconds (of the listener's clock); Home and End go to the ends. */
	function barKey(e: KeyboardEvent) {
		const step = 5000 * rate;
		const at = elapsed * rate;
		const to = e.key === 'ArrowLeft' || e.key === 'ArrowDown' ? at - step
			: e.key === 'ArrowRight' || e.key === 'ArrowUp' ? at + step
			: e.key === 'Home' ? 0
			: e.key === 'End' ? total * rate
			: null;
		if (to == null || !events) return;
		e.preventDefault();
		seek(Math.max(0, to));
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
	<div class="panel" class:big bind:this={panel} role={big ? 'dialog' : undefined} aria-modal={big ? 'true' : undefined} aria-label={big ? tune.name : undefined}>
		{#if big}
			<div class="bighead">
				<span class="name">{tune.name}</span>
				{#if stanzas > 1}<span class="stz">{ta ? `பத்தி ${stanza + 1} / ${stanzas}` : `Stanza ${stanza + 1} of ${stanzas}`}</span>{/if}
				<button type="button" class="exit" onclick={exitBig} aria-label={ta ? 'முழுத் திரையிலிருந்து வெளியேறு' : 'Exit full screen'}>
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
				</button>
			</div>
		{/if}
		{#if svgs}
			<!-- Build output of tools/psalter (Verovio), not user content. -->
			<!-- A tap sings from a note; keyboard users have the timeline below. -->
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
			<div class="score" class:full bind:this={box} role="img" aria-label="{ta ? 'இசைக் குறியீடு' : 'Musical notation for'} {tune.name}" onclick={tapScore}>{@html full ? svgs.full : svgs.incipit}</div>
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
				<div class="bar" bind:this={bar} role="slider" tabindex={events ? 0 : -1}
					aria-label={ta ? 'பாடலில் இடம்' : 'Position in the psalm'} aria-valuemin={0} aria-valuemax={Math.round(total / 1000)}
					aria-valuenow={Math.round(elapsed / 1000)} aria-valuetext="{fmt(elapsed)} / {fmt(total)}"
					onpointerdown={barDown} onpointermove={barMove} onkeydown={barKey}>
					<div class="track"><div class="fill" style="width: {total ? Math.min(100, (elapsed / total) * 100) : 0}%"></div></div>
					<div class="thumb" style="left: {total ? Math.min(100, (elapsed / total) * 100) : 0}%"></div>
				</div>
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
		{#if !big}
			<div class="foot">
				<span>{credit}</span>
				<span class="links">
					<button type="button" class="more" onclick={() => (full = !full)} aria-expanded={full}>{full ? (ta ? 'முதல் வரி' : 'First line') : (ta ? 'முழுப் பண்' : 'Full tune')}</button>
					<button type="button" class="more big-btn" onclick={enterBig} disabled={!svgs}>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg>
						{ta ? 'முழுத் திரை' : 'Full screen'}
					</button>
				</span>
			</div>
		{/if}
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
	/* The timeline: a 4px track in a taller box, so a finger can take hold of it. */
	.bar { position: relative; height: 20px; margin: -8px 0; display: flex; align-items: center; cursor: pointer; touch-action: none; }
	.bar:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }
	.track { flex: 1; height: 4px; border-radius: 999px; background: var(--line); overflow: hidden; }
	.fill { height: 100%; background: var(--accent); }
	.thumb { position: absolute; top: 50%; width: 12px; height: 12px; margin: -6px 0 0 -6px; border-radius: 999px; background: var(--accent); opacity: 0; transition: opacity 0.15s; pointer-events: none; }
	.bar:hover .thumb, .bar:focus-visible .thumb, .bar:active .thumb { opacity: 1; }
	@media (pointer: coarse) { .thumb { opacity: 1; } }
	.score { cursor: pointer; }
	.tempo { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; }
	.tempo .lbl { font-size: 0.74rem; color: var(--muted); margin-right: 0.2rem; }
	.tempo button { display: inline-flex; align-items: baseline; gap: 0.35rem; min-height: 32px; padding: 0.2rem 0.65rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font: inherit; font-size: 0.78rem; font-weight: 600; cursor: pointer; }
	.tempo button:hover { border-color: var(--accent); }
	.tempo button.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.tempo .bpm { font-weight: 400; font-size: 0.72rem; opacity: 0.8; font-variant-numeric: tabular-nums; }
	.foot { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; font-size: 0.74rem; color: var(--muted); }
	.more { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; padding: 0.2rem 0; text-decoration: underline; text-underline-offset: 3px; white-space: nowrap; }
	.links { display: inline-flex; gap: 0.9rem; flex: none; }
	.big-btn { display: inline-flex; align-items: center; gap: 0.3rem; }
	.big-btn:disabled { opacity: 0.5; cursor: default; }

	/* Full screen for singing: the whole tune as large as the screen allows, the controls below. */
	.panel.big { position: fixed; inset: 0; z-index: 1000; border: 0; border-radius: 0; gap: 0.8rem;
		padding: max(0.8rem, env(safe-area-inset-top)) max(1rem, env(safe-area-inset-right)) max(0.8rem, env(safe-area-inset-bottom)) max(1rem, env(safe-area-inset-left)); }
	.panel.big:fullscreen { width: 100vw; height: 100vh; }
	.panel.big::backdrop { background: var(--surface); }
	.bighead { display: flex; align-items: center; gap: 1rem; }
	.bighead .name { font-weight: 700; font-size: 1.1rem; color: var(--ink); }
	.bighead .stz { flex: 1; font-size: 1.05rem; font-weight: 600; color: var(--amber); font-variant-numeric: tabular-nums; }
	.exit { margin-left: auto; width: 44px; height: 44px; border-radius: 999px; border: var(--bw) solid var(--line-2); background: var(--surface-2); color: var(--ink); display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0; }
	.exit:hover { border-color: var(--accent); }
	/* The whole width of the window: a tune taller than the screen scrolls, following the line sung. */
	.panel.big .score { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow-y: auto; overscroll-behavior: contain; }
	.panel.big .score > :global(svg) { margin: auto 0; flex: none; }
	.panel.big .score :global(svg) { width: 100%; height: auto; max-height: none; }
	.panel.big .tempo { justify-content: center; }
</style>

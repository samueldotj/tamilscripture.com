// Going back and forward in a psalm being sung (docs/feature_psalms_explorer.md §8,
// "Seeking"). The same rules as the app's TuneEvents.nearest and Seek.

/** [x, y, id, lyric baseline] as fractions of the drawing (events.json). */
type Head = [number, number, string, number | null];

/**
 * The note nearest a point in the drawing's units (`w` by `h`): to its head or to the word
 * under it, whichever is closer, so a tap on either finds it. -1 when no note is drawn.
 * Noteheads are drawn 80 units right of their recorded x, as the words are.
 */
export function nearestNote(heads: (Head | undefined)[], x: number, y: number, w: number, h: number): number {
	let best = -1;
	let bestD = Infinity;
	heads.forEach((head, i) => {
		if (!head) return;
		const dx = head[0] * w + 80 - x;
		const dy = Math.min(Math.abs(head[1] * h - y), head[3] == null ? Infinity : Math.abs(head[3] * h - y));
		const d = dx * dx + dy * dy * 4; // a system's height matters more than a note's step
		if (d < bestD) {
			bestD = d;
			best = i;
		}
	});
	return best;
}

/**
 * A point in the whole psalm (the audio's own ms, stanzas a breath apart) as a stanza and
 * a position in it. A point in a breath goes to the end of the stanza before it.
 */
export function place(ms: number, once: number, breath: number, stanzas: number): { stanza: number; at: number } {
	const per = once + breath;
	const stanza = Math.max(0, Math.min(stanzas - 1, Math.floor(ms / per)));
	return { stanza, at: Math.max(0, Math.min(once, ms - stanza * per)) };
}

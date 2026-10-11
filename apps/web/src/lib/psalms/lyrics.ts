// Words under the notes (docs/feature_psalms_explorer.md §9): a line's syllables, as the
// build splits them ("shep-", "herd,"), set on the notes that start a syllable in that line
// of the tune (events.json `slots`). Mirrored in the app's Lyrics.kt.

/** Note index → the syllable written under it. Fewer syllables than slots: the last
 *  syllable keeps the line's last note and the one before holds across the gap (a
 *  melisma). More: the extra syllables share the last note, as a feminine ending is sung
 *  ("ri-ver" on one note). */
export function align(syllables: string[], slots: number[]): Map<number, string> {
	const out = new Map<number, string>();
	const s = syllables.length;
	const n = slots.length;
	if (!s || !n) return out;
	if (s <= n) {
		for (let i = 0; i < s - 1; i++) out.set(slots[i], syllables[i]);
		out.set(slots[n - 1], syllables[s - 1]);
	} else {
		for (let i = 0; i < n - 1; i++) out.set(slots[i], syllables[i]);
		out.set(slots[n - 1], join(syllables.slice(n - 1)));
	}
	return out;
}

/** Syllables run together: "ri-" + "ver," is "river,"; separate words keep a space. */
export function join(parts: string[]): string {
	return parts.reduce((acc, p) => (acc.endsWith('-') ? acc.slice(0, -1) + p : acc ? `${acc} ${p}` : p), '');
}

/** A stanza's words on the tune's notes: line by line through `slots`. */
export function stanzaOnNotes(lines: string[][], slots: number[][]): Map<number, string> {
	const out = new Map<number, string>();
	lines.forEach((line, i) => {
		if (slots[i]) for (const [k, v] of align(line, slots[i])) out.set(k, v);
	});
	return out;
}

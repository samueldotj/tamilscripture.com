// Word-level diff, so a reviewer sees the phrase in dispute rather than two
// paragraphs to compare by eye (design 8A). Tamil is written without spaces
// inside a word but with them between words, so splitting on whitespace is the
// right grain here — the same grain the contributor edits in.

export type Op = 'same' | 'add' | 'del';
export interface Piece {
	op: Op;
	text: string;
}

/** Split into words, keeping the whitespace with the word before it. */
function words(s: string): string[] {
	return s.match(/\S+\s*/g) ?? [];
}

/**
 * The longest common subsequence of two word lists, as an edit script.
 * Paragraphs here are a few hundred words at most, so the O(n·m) table is
 * cheaper than the machinery to avoid it.
 */
export function diffWords(before: string, after: string): Piece[] {
	const a = words(before);
	const b = words(after);
	// lcs[i][j] = length of the longest common subsequence of a[i…] and b[j…]
	const lcs: number[][] = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
	for (let i = a.length - 1; i >= 0; i--) {
		for (let j = b.length - 1; j >= 0; j--) {
			lcs[i][j] = a[i].trim() === b[j].trim() ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
		}
	}
	const out: Piece[] = [];
	const push = (op: Op, text: string) => {
		const last = out[out.length - 1];
		if (last && last.op === op) last.text += text;
		else out.push({ op, text });
	};
	let i = 0;
	let j = 0;
	while (i < a.length && j < b.length) {
		if (a[i].trim() === b[j].trim()) {
			push('same', a[i]);
			i++;
			j++;
		} else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
			push('del', a[i++]);
		} else {
			push('add', b[j++]);
		}
	}
	while (i < a.length) push('del', a[i++]);
	while (j < b.length) push('add', b[j++]);
	return out;
}

/** The pieces of `before` that survive, with what was taken out marked. */
export function removed(pieces: Piece[]): Piece[] {
	return pieces.filter((p) => p.op !== 'add');
}
/** The pieces of `after`, with what was put in marked. */
export function added(pieces: Piece[]): Piece[] {
	return pieces.filter((p) => p.op !== 'del');
}

/** True when the two texts differ by more than whitespace. */
export function changed(before: string, after: string): boolean {
	return before.trim().replace(/\s+/g, ' ') !== after.trim().replace(/\s+/g, ' ');
}

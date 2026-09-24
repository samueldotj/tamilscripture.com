// Word-range highlights and notes (R-10.15): the marks each verse draws, the
// notes placed beside each verse, and the word range a text selection covers.
// Offsets count Unicode code points of the verse text (Array.from), the unit
// Verse.svelte cuts its runs in.
import { isPartial, type Highlight, type Note, type TextRange } from '$lib/personal/repo';

/** A stretch of one verse's text: `to` is exclusive and may be Infinity (to the end). */
export interface Mark {
	from: number;
	to: number;
	color?: string;
	note?: boolean;
}

/** A note shown beside the verse it starts in, anchored at character `at`. */
export interface SideNote {
	note: Note;
	at: number;
}

const cp = (s: string) => Array.from(s).length;

/** Per-verse marks for the word-range rows made in `version`. Rows made in
 *  another version are drawn on their whole verses by the caller. */
export function marksByVerse(
	version: string,
	highlights: Highlight[],
	notes: Note[],
	segOf: (verse: number) => string
): Map<string, Mark[]> {
	const out = new Map<string, Mark[]>();
	const add = (r: Highlight | Note, mark: Omit<Mark, 'from' | 'to'>) => {
		if (!isPartial(r) || r.version !== version) return;
		for (let v = r.verse_start; v <= r.verse_end; v++) {
			const id = segOf(v);
			const list = out.get(id) ?? [];
			list.push({ from: v === r.verse_start ? r.char_start! : 0, to: v === r.verse_end ? r.char_end! : Infinity, ...mark });
			out.set(id, list);
		}
	};
	// Older highlights first, so a later colour wins where two overlap.
	for (const h of [...highlights].sort((a, b) => a.updated_at.localeCompare(b.updated_at))) add(h, { color: h.color });
	for (const n of notes) add(n, { note: true });
	return out;
}

/** Notes grouped by the verse they start in, in reading order. */
export function sideNotesByVerse(version: string, notes: Note[], segOf: (verse: number) => string): Map<string, SideNote[]> {
	const out = new Map<string, SideNote[]>();
	const sorted = [...notes].sort((a, b) => a.verse_start - b.verse_start || (a.char_start ?? 0) - (b.char_start ?? 0));
	for (const n of sorted) {
		const id = segOf(n.verse_start);
		const at = isPartial(n) && n.version === version ? n.char_start! : 0;
		out.set(id, [...(out.get(id) ?? []), { note: n, at }]);
	}
	return out;
}

/** Character offset of a DOM point within a verse element, counted over its
 *  text runs (`[data-o]`) so verse numbers, markers and notes are skipped. */
function pointOffset(verse: HTMLElement, node: Node, offset: number): number {
	let end = 0;
	for (const run of verse.querySelectorAll<HTMLElement>('[data-o]')) {
		const o = Number(run.dataset.o);
		const whole = document.createRange();
		whole.selectNodeContents(run);
		let c: number;
		try { c = whole.comparePoint(node, offset); } catch { return end; }
		if (c < 0) return o;
		if (c === 0) {
			const pre = document.createRange();
			pre.setStart(run, 0);
			pre.setEnd(node, offset);
			return o + cp(pre.toString());
		}
		end = o + cp(run.textContent ?? '');
	}
	return end;
}

/**
 * The verses a text selection touches and, when it covers only part of them,
 * the word range. Leading and trailing spaces are left out, and a verse the
 * selection only grazes at its very edge is not counted.
 */
export function selectionRange(
	verses: HTMLElement[],
	range: Range,
	version: string,
	textOf: (id: string) => string
): { ids: string[]; range: TextRange | null } {
	if (!verses.length) return { ids: [], range: null };
	const num = (el: HTMLElement) => Number(el.dataset.verse!.split('.')[2]);
	let list = [...verses];
	let cs = pointOffset(list[0], range.startContainer, range.startOffset);
	let ce = pointOffset(list[list.length - 1], range.endContainer, range.endOffset);
	const text = (el: HTMLElement) => Array.from(textOf(el.dataset.verse!));
	if (list.length > 1 && cs >= text(list[0]).length) { list = list.slice(1); cs = 0; }
	if (list.length > 1 && ce <= 0) { list = list.slice(0, -1); ce = text(list[list.length - 1]).length; }
	const first = text(list[0]), last = text(list[list.length - 1]);
	let lead = 0, tail = last.length;
	while (lead < first.length && /\s/.test(first[lead])) lead++;
	while (tail > 0 && /\s/.test(last[tail - 1])) tail--;
	while (cs < first.length && /\s/.test(first[cs])) cs++;
	while (ce > 0 && /\s/.test(last[ce - 1])) ce--;
	const ids = list.map((el) => el.dataset.verse!);
	const single = list.length === 1;
	if (single && ce <= cs) return { ids, range: null };
	if (cs <= lead && ce >= tail) return { ids, range: null };
	const quote = single
		? first.slice(cs, ce).join('')
		: [first.slice(cs).join(''), ...list.slice(1, -1).map((el) => textOf(el.dataset.verse!)), last.slice(0, ce).join('')].join(' ');
	return {
		ids,
		range: {
			version,
			verse_start: num(list[0]),
			char_start: cs,
			verse_end: num(list[list.length - 1]),
			char_end: ce,
			quote: quote.replace(/\s+/g, ' ').trim().slice(0, 1000)
		}
	};
}

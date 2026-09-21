// Dictionary words in the text (design 7A, task 7.15): which words of each
// verse are a person or place named there. Built from the chapter's mentions,
// which carry the Tamil forms that actually occur in the chapter.
import type { VersionMeta } from '$lib/content/types';
import type { ChapterMentions } from '$lib/entities/types';

export interface NameHit {
	id: string;
	kind: 'person' | 'place';
}

export interface VerseNames {
	re: RegExp;
	byForm: Map<string, NameHit>;
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** verse id → the pattern of names to mark in it, for one version's text. */
export function nameIndex(m: ChapterMentions | null, version: VersionMeta): Map<string, VerseNames> {
	const out = new Map<string, VerseNames>();
	if (!m) return out;
	const formsOf = (s: { name_en: string; name_ta?: string | null; forms?: Record<string, string[]> | null }): string[] => {
		if (version.lang === 'ta') return s.forms?.[version.code] ?? [];
		return [s.name_en];
	};
	for (const v of m.verses) {
		const byForm = new Map<string, NameHit>();
		const add = (id: string, kind: NameHit['kind'], forms: string[]) => {
			for (const f of forms) if (f && !byForm.has(f)) byForm.set(f, { id, kind });
		};
		for (const id of v.people ?? []) {
			const p = m.people?.[id];
			if (p) add(id, 'person', formsOf(p));
		}
		for (const id of v.places ?? []) {
			const p = m.places[id];
			if (p) add(id, 'place', formsOf(p));
		}
		if (!byForm.size) continue;
		// Longest first, so "பவுலையும்" wins over "பவுல்"; a match must not sit
		// inside a longer word (letters and Tamil vowel signs both count).
		const alt = [...byForm.keys()].sort((a, b) => b.length - a.length).map(escape).join('|');
		out.set(v.verse, { re: new RegExp(`(?<![\\p{L}\\p{M}])(${alt})(?![\\p{L}\\p{M}])`, 'gu'), byForm });
	}
	return out;
}

/** Split text into plain pieces and marked names. */
export function splitNames(text: string, names: VerseNames | null | undefined): { t: string; hit?: NameHit }[] {
	if (!names || !text) return [{ t: text }];
	const out: { t: string; hit?: NameHit }[] = [];
	let last = 0;
	names.re.lastIndex = 0;
	for (const m of text.matchAll(names.re)) {
		const at = m.index ?? 0;
		if (at > last) out.push({ t: text.slice(last, at) });
		out.push({ t: m[0], hit: names.byForm.get(m[0]) });
		last = at + m[0].length;
	}
	if (last < text.length) out.push({ t: text.slice(last) });
	return out;
}

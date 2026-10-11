// Filtering for the Psalms explorer (docs/feature_psalms_explorer.md §1): any
// value within a facet, every facet that has a selection. Genre ids and
// collection ids share the Genre panel; "anonymous" is the Author chip for a
// psalm with no named author. No Svelte here; the app mirrors this in
// PsalmFilter.kt and both run data/fixtures/psalms-filter.json.
import type { Psalm, PsalmsIndex } from './types';

export const ANONYMOUS = 'anonymous';

export interface Selection {
	themes: string[];
	/** genre and collection ids */
	genres: string[];
	/** author ids, or ANONYMOUS */
	authors: string[];
}

export const EMPTY: Selection = { themes: [], genres: [], authors: [] };

export function isEmpty(s: Selection): boolean {
	return !s.themes.length && !s.genres.length && !s.authors.length;
}

export function count(s: Selection): number {
	return s.themes.length + s.genres.length + s.authors.length;
}

/** A predicate for the psalms a selection keeps. */
export function matcher(index: PsalmsIndex, s: Selection): (p: Psalm) => boolean {
	const inCollection = new Set<number>();
	for (const c of index.collections) if (s.genres.includes(c.id)) c.psalms.forEach((n) => inCollection.add(n));
	return (p) =>
		(!s.themes.length || s.themes.includes(p.theme)) &&
		(!s.genres.length || p.genres.some((g) => s.genres.includes(g)) || inCollection.has(p.n)) &&
		(!s.authors.length || p.authors.some((a) => s.authors.includes(a)) || (!p.authors.length && s.authors.includes(ANONYMOUS)));
}

/** `list` with `value` added, or removed when already there. */
export function toggled<T>(list: T[], value: T): T[] {
	return list.includes(value) ? list.filter((x) => x !== value) : [...list, value];
}

/** Query string for a selection and open psalm: `p=23&theme=lament&genre=trust,petition&author=david`. */
export function toQuery(s: Selection, psalm: number): string {
	const q = new URLSearchParams();
	q.set('p', String(psalm));
	if (s.themes.length) q.set('theme', s.themes.join(','));
	if (s.genres.length) q.set('genre', s.genres.join(','));
	if (s.authors.length) q.set('author', s.authors.join(','));
	return q.toString().replace(/%2C/g, ',');
}

/** The selection and psalm in a URL, keeping only ids the index knows. */
export function fromQuery(index: PsalmsIndex, q: URLSearchParams): { selection: Selection; psalm: number } {
	const list = (k: string) => (q.get(k) ?? '').split(',').filter(Boolean);
	const themes = new Set(index.themes.map((t) => t.id));
	const genres = new Set([...index.genres.map((g) => g.id), ...index.collections.map((c) => c.id)]);
	const authors = new Set([...index.authors.map((a) => a.id), ANONYMOUS]);
	const n = Number(q.get('p'));
	return {
		selection: {
			themes: list('theme').filter((x) => themes.has(x)),
			genres: list('genre').filter((x) => genres.has(x)),
			authors: list('author').filter((x) => authors.has(x))
		},
		psalm: Number.isInteger(n) && n >= 1 && n <= 150 ? n : 23
	};
}

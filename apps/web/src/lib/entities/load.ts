// Loaders for the entity content written by entity-ingest (M6). All static
// files under /content/{build}/entities/, so they cache like chapter JSON.
import { contentUrl, findBook } from '$lib/content/manifest';
import type { ChapterMentions, Glossary, Journey, Place, PlaceIndex } from './types';

type Fetch = typeof fetch;

async function getJson<T>(fetch: Fetch, path: string): Promise<T> {
	const res = await fetch(contentUrl(path));
	if (!res.ok) throw new Error(`${res.status} loading ${path}`);
	return (await res.json()) as T;
}

/** Inline SVG text for a static map, or null when the chapter has none. */
export async function loadMapSvg(fetch: Fetch, path: string): Promise<string | null> {
	const res = await fetch(contentUrl(`entities/maps/${path}.svg`));
	if (!res.ok) return null;
	return res.text();
}

let indexPromise: Promise<PlaceIndex> | null = null;
export function loadPlaceIndex(fetch: Fetch): Promise<PlaceIndex> {
	if (!indexPromise) indexPromise = getJson<PlaceIndex>(fetch, 'entities/places.json');
	return indexPromise;
}

export function loadPlace(fetch: Fetch, id: string): Promise<Place> {
	return getJson<Place>(fetch, `entities/place/${id}.json`);
}

/** Mentions for a chapter; null when the chapter names no places. */
export async function loadMentions(fetch: Fetch, book: string, chapter: number): Promise<ChapterMentions | null> {
	const res = await fetch(contentUrl(`entities/mentions/${book}/${chapter}.json`));
	if (!res.ok) return null;
	return (await res.json()) as ChapterMentions;
}

let journeysPromise: Promise<Journey[]> | null = null;
export function loadJourneys(fetch: Fetch): Promise<Journey[]> {
	if (!journeysPromise) journeysPromise = getJson<Journey[]>(fetch, 'entities/journeys.json');
	return journeysPromise;
}

let glossaryPromise: Promise<Glossary> | null = null;
export function loadGlossary(fetch: Fetch): Promise<Glossary> {
	if (!glossaryPromise) glossaryPromise = getJson<Glossary>(fetch, 'entities/glossary.json');
	return glossaryPromise;
}

/** Display name for a place in the interface language. */
export function placeName(p: { name_en: string; name_ta?: string; qualifier?: string }, lang: 'ta' | 'en'): string {
	const base = lang === 'ta' && p.name_ta ? p.name_ta : p.name_en;
	return p.qualifier ? `${base} (${p.qualifier})` : base;
}

/** Tamil label for a full place record: default Tamil version first. */
export function placeLabelTa(p: Place, preferred = 'IRVTAM'): string | undefined {
	return p.names_ta[preferred]?.label ?? Object.values(p.names_ta)[0]?.label;
}

/** Human verse label from an id like `GEN.14.15`. */
export function verseLabel(id: string, lang: 'ta' | 'en'): string {
	const [code, ch, v] = id.split('.');
	const book = findBook(code);
	if (!book) return id;
	return `${lang === 'ta' ? book.name_ta : book.name_en} ${ch}:${v}`;
}

/** Group verse ids by book in canonical order: [book code, verse ids]. */
export function groupByBook(verses: string[]): [string, string[]][] {
	const map = new Map<string, string[]>();
	for (const v of verses) {
		const code = v.split('.')[0];
		if (!map.has(code)) map.set(code, []);
		map.get(code)!.push(v);
	}
	return [...map.entries()].sort((a, b) => (findBook(a[0])?.order ?? 0) - (findBook(b[0])?.order ?? 0));
}

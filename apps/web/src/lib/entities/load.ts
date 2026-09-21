// Loaders for the entity content written by entity-ingest (M6, M7). All static
// files under /content/{build}/entities/, so they cache like chapter JSON.
import { contentUrl, findBook } from '$lib/content/manifest';
import type { Article, ArticleIndexEntry, ChapterMentions, Glossary, Journey, Person, PersonIndexEntry, Place, PlaceIndex } from './types';

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

let peoplePromise: Promise<PersonIndexEntry[]> | null = null;
/** One Strong's number with every verse it occurs in (docs/feature_concordance.md). */
export interface StrongsEntry {
	s: string;
	script: 'he' | 'el';
	lemma: string;
	translit: string;
	/** STEP's part-of-speech code, e.g. `H:N-M`, `G:V` */
	pos: string;
	gloss: string;
	def: string;
	/** words carrying the number (a verse can hold it more than once) */
	count: number;
	/** [book code, verses] in canonical order */
	books: [string, number][];
	/** verse keys (book order × 10⁶ + chapter × 10³ + verse), delta-encoded */
	v: number[];
	/** surface forms, and for each verse the index of the form it uses */
	f: string[];
	fi: number[];
	names: { kind: 'person' | 'place'; id: string; name_en: string; name_ta?: string | null; brief?: string }[];
	renderings: string[];
	/** Tamil meaning (concordance C5), with where it came from */
	gloss_ta?: string | null;
	gloss_ta_source?: 'draft' | 'community' | 'owner' | null;
}

/** STEP disambiguates past Z with lower-case letters; those files carry an underscore. */
export function strongsFile(num: string): string {
	const last = num.slice(-1);
	return /[a-z]/.test(last) ? `${num.slice(0, -1)}_${last}` : num;
}

export function loadStrongs(fetch: Fetch, num: string): Promise<StrongsEntry> {
	return getJson<StrongsEntry>(fetch, `entities/strongs/${strongsFile(num)}.json`);
}

/** A chapter's original words: verse number → [text, transliteration, gloss, Strong's, morphology][]. */
export interface OriginalChapter {
	book: string;
	chapter: number;
	lang: 'he' | 'el';
	verses: Record<string, [string, string, string, string, string][]>;
}

const originalCache = new Map<string, Promise<OriginalChapter>>();
export function loadOriginal(fetch: Fetch, book: string, chapter: number): Promise<OriginalChapter> {
	const key = `${book}.${chapter}`;
	if (!originalCache.has(key)) {
		const p = getJson<OriginalChapter>(fetch, `entities/original/${book}/${chapter}.json`);
		p.catch(() => originalCache.delete(key));
		originalCache.set(key, p);
	}
	return originalCache.get(key)!;
}

/** [number, lemma, transliteration, gloss, verses, Tamil gloss] for every page; server-side search and sitemaps. */
export function loadStrongsIndex(fetch: Fetch): Promise<[string, string, string, string, number, string?][]> {
	return getJson(fetch, 'entities/strongs/index.json');
}

export function loadPeopleIndex(fetch: Fetch): Promise<PersonIndexEntry[]> {
	if (!peoplePromise) peoplePromise = getJson<PersonIndexEntry[]>(fetch, 'entities/people.json');
	return peoplePromise;
}

export function loadPerson(fetch: Fetch, id: string): Promise<Person> {
	return getJson<Person>(fetch, `entities/person/${id}.json`);
}

let articleIndexPromise: Promise<ArticleIndexEntry[]> | null = null;
export function loadArticleIndex(fetch: Fetch): Promise<ArticleIndexEntry[]> {
	if (!articleIndexPromise) articleIndexPromise = getJson<ArticleIndexEntry[]>(fetch, 'entities/articles/index.json');
	return articleIndexPromise;
}

/** `id` is `{source}/{slug}`. */
export function loadArticle(fetch: Fetch, id: string): Promise<Article> {
	return getJson<Article>(fetch, `entities/articles/${id}.json`);
}

/** Mentions for a chapter; null when the chapter names no places or people. */
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

/** Display name for a place or person in the interface language. */
export function placeName(p: { name_en: string; name_ta?: string | null; qualifier?: string | null }, lang: 'ta' | 'en'): string {
	const base = lang === 'ta' && p.name_ta ? p.name_ta : p.name_en;
	return p.qualifier ? `${base} (${p.qualifier})` : base;
}

/** Tamil label for a full entity record: default Tamil version first. */
export function placeLabelTa(p: { names_ta: Record<string, { label: string }> }, preferred = 'IRVTAM'): string | undefined {
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

/** Path for an entity reference like `place/damascus` or `person/paul`. */
export function entityHref(ref: string): string {
	return `/${ref}`;
}

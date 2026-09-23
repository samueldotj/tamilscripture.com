// The site's public URLs, shared by the XML sitemaps and /sitemap.txt so the two never drift.
import { chapterUrl, manifest, verseUrl } from '$lib/content/manifest';
import { loadChapter } from '$lib/content/load';
import type { VersionMeta } from '$lib/content/types';
import { loadArticleIndex, loadJourneys, loadPeopleIndex, loadPlaceIndex, loadStrongsIndex } from '$lib/entities/load';

export const ORIGIN = 'https://www.tamilscripture.com';

type Fetch = typeof fetch;

/** Pages that are not a chapter or an entity. The heatmaps and the map explorer
 *  are noindex (they hold no text of their own), so they are left out. */
export const PAGE_PATHS = ['/', '/about', '/licences'];

/** Every book and chapter page of one version. */
export function chapterPaths(version: VersionMeta): string[] {
	const vp = version.code.toLowerCase();
	const paths: string[] = [];
	for (const book of manifest.books) {
		if (!version.books.includes(book.code)) continue;
		paths.push(chapterUrl(vp, book));
		for (let c = 1; c <= book.chapters; c++) paths.push(chapterUrl(vp, book, c));
	}
	return paths;
}

/** Every single-verse page of one version (/irvtam/john/3.16), one per verse the text has.
 *  Reads each chapter's JSON, so it runs at build time (the sitemap is prerendered). */
export async function versePaths(fetch: Fetch, version: VersionMeta): Promise<string[]> {
	const vp = version.code.toLowerCase();
	const books = manifest.books.filter((b) => version.books.includes(b.code));
	const perBook = await Promise.all(
		books.map(async (book) => {
			const paths: string[] = [];
			for (let c = 1; c <= book.chapters; c++) {
				const ch = await loadChapter(fetch, version.code, book.code, c);
				const verses = new Set<number>();
				for (const b of ch.blocks) {
					if (b.type !== 'para') continue;
					for (const seg of b.segments) {
						const n = Number(seg.id?.split('.')[2]);
						if (n) verses.add(n);
					}
				}
				for (const v of [...verses].sort((a, b) => a - b)) paths.push(verseUrl(vp, book, c, `${v}`));
			}
			return paths;
		})
	);
	return perBook.flat();
}

/** Atlas, journeys, places, people and dictionary articles, from the content indexes. */
export async function entityPaths(fetch: Fetch): Promise<string[]> {
	const [index, journeys, people, articles, strongs] = await Promise.all([
		loadPlaceIndex(fetch).catch(() => null),
		loadJourneys(fetch).catch(() => []),
		loadPeopleIndex(fetch).catch(() => []),
		loadArticleIndex(fetch).catch(() => []),
		loadStrongsIndex(fetch).catch(() => [])
	]);
	return [
		'/atlas',
		'/dictionary',
		...journeys.map((j) => `/atlas/${j.id}`),
		...(index?.places ?? []).map((p) => `/place/${p.id}`),
		...people.map((p) => `/person/${p.id}`),
		...articles.map((a) => `/dictionary/${a.id}`),
		...strongs.map((s) => `/strongs/${s[0]}`)
	];
}

export function urlset(paths: string[]): string {
	const urls = paths.map((p) => `  <url><loc>${ORIGIN}${p}</loc></url>`).join('\n');
	return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
}

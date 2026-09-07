import { error, redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { chapterUrl, findBook, findVersion } from '$lib/content/manifest';
import { loadChapter } from '$lib/content/load';

// Rendered on first request and cached at the edge until the next deploy
// (ADR-1). Prerendering every chapter is not possible on Vercel: the adapter
// emits two routes per prerendered page and the platform caps routes at 2,048.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch, url }) => {
	const codes = params.versions.split('+');
	const versions = codes.map((c) => findVersion(c)!);
	const book = findBook(params.book)!;
	const chapter = Number(params.chapter);
	if (chapter > book.chapters) error(404, 'No such chapter');
	if (!versions.every((v) => v.books.includes(book.code))) error(404, 'Book not available in this version');

	// One canonical URL: lowercase version codes and the primary slug.
	const canonicalVersions = versions.map((v) => v.code.toLowerCase()).join('+');
	const canonical = chapterUrl(canonicalVersions, book, chapter);
	if (`/${params.versions}/${params.book}/${params.chapter}` !== canonical) {
		redirect(301, canonical);
	}

	// Absolute URL so the server-side render fetches the static JSON from the
	// same deployment; in the browser this is the CDN path.
	const absolute: typeof fetch = (input, init) =>
		fetch(typeof input === 'string' ? new URL(input, url.origin) : input, init);
	const chapters = await Promise.all(
		versions.map((v) => loadChapter(absolute, v.code, book.code, chapter))
	);
	return { versions, book, chapter, chapters, canonical };
};

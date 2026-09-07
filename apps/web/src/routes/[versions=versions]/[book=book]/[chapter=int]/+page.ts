import { error, redirect } from '@sveltejs/kit';
import type { EntryGenerator, PageLoad } from './$types';
import { chapterUrl, findBook, findVersion, manifest } from '$lib/content/manifest';
import { loadChapter } from '$lib/content/load';

export const prerender = true;

export const entries: EntryGenerator = () =>
	manifest.versions.flatMap((v) =>
		manifest.books
			.filter((b) => v.books.includes(b.code))
			.flatMap((b) =>
				Array.from({ length: b.chapters }, (_, i) => ({
					versions: v.code.toLowerCase(),
					book: b.slug,
					chapter: String(i + 1)
				}))
			)
	);

export const load: PageLoad = async ({ params, fetch }) => {
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

	const chapters = await Promise.all(versions.map((v) => loadChapter(fetch, v.code, book.code, chapter)));
	return { versions, book, chapter, chapters, canonical };
};

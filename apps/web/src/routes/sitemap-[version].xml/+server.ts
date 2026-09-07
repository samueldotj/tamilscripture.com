import { error } from '@sveltejs/kit';
import type { EntryGenerator, RequestHandler } from './$types';
import { chapterUrl, findVersion, manifest } from '$lib/content/manifest';

export const prerender = true;
export const entries: EntryGenerator = () => manifest.versions.map((v) => ({ version: v.code.toLowerCase() }));

const ORIGIN = 'https://www.tamilscripture.com';

export const GET: RequestHandler = ({ params }) => {
	const version = findVersion(params.version);
	if (!version) error(404);
	const vp = version.code.toLowerCase();
	const urls: string[] = [];
	for (const book of manifest.books) {
		if (!version.books.includes(book.code)) continue;
		urls.push(`  <url><loc>${ORIGIN}${chapterUrl(vp, book)}</loc></url>`);
		for (let c = 1; c <= book.chapters; c++) {
			urls.push(`  <url><loc>${ORIGIN}${chapterUrl(vp, book, c)}</loc></url>`);
		}
	}
	const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`;
	return new Response(xml, { headers: { 'content-type': 'application/xml' } });
};

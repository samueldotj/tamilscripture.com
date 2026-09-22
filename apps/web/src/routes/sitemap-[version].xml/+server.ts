import { error } from '@sveltejs/kit';
import type { EntryGenerator, RequestHandler } from './$types';
import { DEFAULT_VERSION, findVersion } from '$lib/content/manifest';
import { chapterPaths, urlset } from '$lib/seo/sitemap';

export const prerender = true;
// Only the canonical version is listed: the other versions' pages carry its URL as their canonical (ADR-15).
export const entries: EntryGenerator = () => [{ version: DEFAULT_VERSION.toLowerCase() }];

export const GET: RequestHandler = ({ params }) => {
	const version = findVersion(params.version);
	if (!version || version.code !== DEFAULT_VERSION) error(404);
	return new Response(urlset(chapterPaths(version)), { headers: { 'content-type': 'application/xml' } });
};

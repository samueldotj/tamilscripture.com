import { error } from '@sveltejs/kit';
import type { EntryGenerator, RequestHandler } from './$types';
import { findVersion, manifest } from '$lib/content/manifest';
import { chapterPaths, urlset } from '$lib/seo/sitemap';

export const prerender = true;
export const entries: EntryGenerator = () => manifest.versions.map((v) => ({ version: v.code.toLowerCase() }));

export const GET: RequestHandler = ({ params }) => {
	const version = findVersion(params.version);
	if (!version) error(404);
	return new Response(urlset(chapterPaths(version)), { headers: { 'content-type': 'application/xml' } });
};

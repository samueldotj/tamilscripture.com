import type { RequestHandler } from './$types';
import { DEFAULT_VERSION, findVersion } from '$lib/content/manifest';
import { urlset, versePaths } from '$lib/seo/sitemap';

// Built once per deploy: it reads every chapter of the canonical version to list its verses.
export const prerender = true;

// The canonical version's single-verse pages; the other versions' copies name these as canonical (ADR-15).
export const GET: RequestHandler = async ({ fetch }) =>
	new Response(urlset(await versePaths(fetch, findVersion(DEFAULT_VERSION)!)), { headers: { 'content-type': 'application/xml' } });

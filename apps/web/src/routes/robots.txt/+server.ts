import type { RequestHandler } from './$types';
import { manifest } from '$lib/content/manifest';

// Built from the manifest so a version added by config (M5 5.12) gets the same rules.
export const prerender = true;

// Crawlers are kept to one copy of each passage. Two-version pages (/irvtam+kjv/…)
// and verse ranges (/irvtam/john/3/16-18, /irvtam/john/3.16-18) name a canonical
// page already, but every one of them is rendered and cached on first request,
// and there are millions of them; a crawler walking them all was most of the
// site's ISR writes. Single chapters and single verses stay open. The rules are
// anchored on a version code rather than on bare wildcards, which would also
// match app bundles such as /_app/immutable/chunks/a-b.js that search engines
// need to render the page.
export const GET: RequestHandler = () => {
	const lines = [
		'# https://www.robotstxt.org/robotstxt.html',
		'User-agent: *',
		'Allow: /',
		'Disallow: /me/',
		'Disallow: /api/',
		'# Rendered in the browser only, so their noindex tag is invisible without JavaScript.',
		'Disallow: /mod',
		'Disallow: /present/*/edit',
		'Disallow: /present/*/stats',
		'# Two versions side by side, and verse ranges: see the canonical single-version, single-verse pages.'
	];
	for (const v of manifest.versions) {
		const code = v.code.toLowerCase();
		lines.push(`Disallow: /${code}+`, `Disallow: /${code}/*/*/*-`, `Disallow: /${code}/*.*-`);
	}
	lines.push(
		'',
		'Sitemap: https://www.tamilscripture.com/sitemap.xml',
		'Sitemap: https://www.tamilscripture.com/sitemap.txt'
	);
	return new Response(lines.join('\n') + '\n', { headers: { 'content-type': 'text/plain; charset=utf-8' } });
};

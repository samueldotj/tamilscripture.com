import type { Handle } from '@sveltejs/kit';
import { pageLang } from '$lib/content/page-lang';

// app.html says lang="ta"; an English version's pages (BSB, WEB, KJV) say "en"
// so screen readers and search engines read them as English.
export const handle: Handle = ({ event, resolve }) => {
	const lang = pageLang(event.params.versions);
	if (lang === 'ta') return resolve(event);
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('<html lang="ta"', `<html lang="${lang}"`)
	});
};

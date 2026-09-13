import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import { loadArticle, loadPeopleIndex, loadPlaceIndex } from '$lib/entities/load';

// Article pages render on first request and are cached at the edge until the
// next deploy (ADR-1): 3,962 articles would exceed Vercel's route cap if prerendered.
export const prerender = false;
export const config = { isr: { expiration: false } };

export const load: PageLoad = async ({ params, fetch }) => {
	const article = await loadArticle(fetch, `${params.source}/${params.id}`).catch(() => null);
	if (!article) error(404, 'Unknown article');
	// Names for the linked entities, so the page can show them in Tamil.
	const wantsPlaces = article.entities.some((e) => e.startsWith('place/'));
	const wantsPeople = article.entities.some((e) => e.startsWith('person/'));
	const [places, people] = await Promise.all([
		wantsPlaces ? loadPlaceIndex(fetch).then((i) => i.places).catch(() => []) : [],
		wantsPeople ? loadPeopleIndex(fetch).catch(() => []) : []
	]);
	const linked = article.entities.flatMap((ref) => {
		const [kind, id] = ref.split('/');
		const hit = kind === 'place' ? places.find((p) => p.id === id) : people.find((p) => p.id === id);
		return hit ? [{ ref, kind, id, name_en: hit.name_en, name_ta: hit.name_ta, qualifier: hit.qualifier }] : [];
	});
	return { article, linked };
};

// Shared journey presentation: chronological order and the colour/line style
// each journey is drawn with, so the atlas index, the explore map and its
// journey list all agree.
import type { Glossary, Journey } from './types';

/** How many hues `--j-1 … --j-8` there are in app.css. */
export const HUES = 8;
/** Line styles that pair with the hues, so hue × style is unique for 32 journeys. */
export const DASHES: (number[] | undefined)[] = [undefined, [2, 1.5], [0.4, 1.6], [4, 1.4, 0.6, 1.4]];

export interface JourneyStyle {
	/** `var(--j-N)` — resolves per theme. */
	color: string;
	/** MapLibre line-dasharray, or undefined for a solid line. */
	dash: number[] | undefined;
	/** SVG dasharray for the swatch in the list. */
	swatchDash: string;
}

/** Style for the journey at `i` in chronological order. Stable: it depends on
 *  the position in the full list, not on how many are currently shown. */
export function journeyStyle(i: number): JourneyStyle {
	const dash = DASHES[Math.floor(i / HUES) % DASHES.length];
	return {
		color: `var(--j-${(i % HUES) + 1})`,
		dash,
		// The map scales dasharray by line width (3px); the swatch stroke is 3px too.
		swatchDash: dash ? dash.map((n) => n * 3).join(' ') : 'none'
	};
}

/** Chronological order: the glossary lists the periods in it, and journeys.toml
 *  lists the journeys of a period in it. Both come from the content build, so
 *  this only has to keep the file order and rank the periods. */
export function sortJourneys(journeys: Journey[], glossary: Glossary | null): Journey[] {
	const order = Object.keys(glossary?.periods ?? {});
	const rank = (p: string) => {
		const i = order.indexOf(p);
		return i < 0 ? order.length : i;
	};
	return [...journeys].sort((a, b) => rank(a.period) - rank(b.period));
}

/** Journeys grouped into their periods, both in chronological order. */
export function byPeriod(journeys: Journey[]): { period: string; journeys: Journey[] }[] {
	const groups: { period: string; journeys: Journey[] }[] = [];
	for (const j of journeys) {
		const last = groups[groups.length - 1];
		if (last?.period === j.period) last.journeys.push(j);
		else groups.push({ period: j.period, journeys: [j] });
	}
	return groups;
}

// The atlas timeline: Cliopatria polity borders (CC BY 4.0), one row per
// polity per period. The whole file is loaded once and filtered by year in the
// browser, so moving the slider costs no requests.
import { contentUrl } from '$lib/content/manifest';
import { HUES } from './journeys';

export interface Polity {
	id: string;
	name_en: string;
	name_ta?: string;
	/** True while no maintainer has confirmed the Tamil name. */
	draft_ta?: boolean;
	/** Inclusive years this row's borders apply to; negative is BCE. */
	from: number;
	to: number;
	/** A point inside the polygon, for the label. */
	lon: number;
	lat: number;
	/** Widest side of its bounding box in degrees: is there room to label it? */
	span: number;
	wikipedia?: string;
	wikidata?: string;
}

export interface PolityCollection {
	type: 'FeatureCollection';
	features: { type: 'Feature'; properties: Polity; geometry: unknown }[];
}

export interface Timeline {
	/** The collection itself, handed to MapLibre so it is fetched once. */
	fc: PolityCollection;
	rows: Polity[];
	/** Every year at which something appears, changes or ends, ascending. */
	years: number[];
}

/** The era the atlas covers. Cliopatria itself starts at 3400 BCE, and the end
 *  is set by the last council on the timeline, the second of Nicaea in 787. */
export const FIRST_YEAR = -4000;
export const LAST_YEAR = 800;

let promise: Promise<Timeline> | null = null;
export function loadTimeline(fetch: typeof globalThis.fetch): Promise<Timeline> {
	if (!promise) {
		promise = (async () => {
			const res = await fetch(contentUrl('entities/geo/polities/polities.geojson'));
			if (!res.ok) throw new Error(`${res.status} loading polities`);
			const fc = (await res.json()) as PolityCollection;
			const rows = fc.features.map((f) => f.properties);
			const set = new Set<number>();
			for (const r of rows) {
				set.add(Math.max(r.from, FIRST_YEAR));
				if (r.to < LAST_YEAR) set.add(r.to + 1);
			}
			return { fc, rows, years: [...set].sort((a, b) => a - b) };
		})();
	}
	return promise;
}

/** A polity's hue, from its id, so it keeps the same colour down the timeline
 *  however many others are on the map beside it. */
export function polityHue(id: string): number {
	let h = 0;
	for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
	return h % HUES;
}

/** "1400 BCE" / "AD 33", and the Tamil equivalents. */
export function yearLabel(year: number, ta: boolean): string {
	if (year < 0) return ta ? `கி.மு. ${-year}` : `${-year} BCE`;
	return ta ? `கி.பி. ${year}` : `AD ${year}`;
}

/** The row of a polity that covers `year`, or nothing. */
export function at(rows: Polity[], year: number): Polity[] {
	return rows.filter((r) => r.from <= year && year <= r.to);
}

export function polityName(p: Polity, lang: 'ta' | 'en'): string {
	return lang === 'ta' && p.name_ta ? p.name_ta : p.name_en;
}

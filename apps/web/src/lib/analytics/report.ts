// The moderators' traffic report (docs/feature_analytics.md §4). Staff-only
// RPCs in Postgres; readers get null.
import { sb } from '$lib/supabase/client';

export interface Totals {
	views: number;
	visitors: number;
	unique_views: number;
	members: number;
	verse_clicks: number;
	/** Audio Bible (A7): chapters started, by a reader or by continuing */
	audio_starts: number;
	/** visitors who played audio, per day, summed */
	listeners: number;
	/** seconds heard */
	listen_seconds: number;
	/** chapters heard to the end */
	audio_ends: number;
}
export type Measure = keyof Totals;
export interface Day extends Totals {
	day: string;
}
export interface Row {
	key: string;
	/** country for a city row, language for a search */
	extra: string | null;
	/** events (for searches: times searched; for empty searches: times with no result) */
	n: number;
	/** visitors, per day, summed (for searches: times with no result; for empty searches: times searched) */
	u: number;
}
export type Dimension =
	| 'pages'
	| 'sections'
	| 'books'
	| 'chapters'
	| 'verses'
	| 'verse_books'
	| 'countries'
	| 'cities'
	| 'devices'
	| 'os'
	| 'browsers'
	| 'screens'
	| 'referrers'
	| 'langs'
	| 'audio_versions'
	| 'audio_time'
	| 'audio_chapters'
	| 'audio_sources'
	| 'audio_verses';
export interface Report {
	from: string;
	to: string;
	totals: Totals;
	/** the same length of time just before `from` */
	previous: Totals;
	daily: Day[];
	top: Partial<Record<Dimension, Row[]>>;
	searches: Row[];
	searches_empty: Row[];
}
export interface Now {
	views: number;
	visitors: number;
	verse_clicks: number;
	listeners: number;
	pages: { key: string; n: number }[];
	/** chapters being heard: key BOOK.chapter, extra version, n listeners */
	listening: { key: string; extra: string | null; n: number }[];
	countries: { key: string; n: number }[];
}

/** India time, the day the server counts in. */
export function istToday(): Date {
	const now = new Date();
	return new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60_000);
}
export function isoDay(d: Date): string {
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export async function loadReport(days: number): Promise<Report | null> {
	const to = istToday();
	const from = new Date(to);
	from.setDate(from.getDate() - (days - 1));
	const { data, error } = await (await sb()).rpc('analytics_report', { p_from: isoDay(from), p_to: isoDay(to) });
	if (error) throw new Error(error.message);
	return (data as Report | null) ?? null;
}

export async function loadNow(): Promise<Now | null> {
	const { data, error } = await (await sb()).rpc('analytics_now');
	if (error) throw new Error(error.message);
	return (data as Now | null) ?? null;
}

/** A spike: a day above three times the range's median and at least 20. */
export function spikes(daily: Day[], measure: Measure): { day: string; value: number; times: number }[] {
	const values = daily.map((d) => d[measure]).filter((v) => v > 0).sort((a, b) => a - b);
	if (values.length < 5) return [];
	const median = values[Math.floor(values.length / 2)];
	if (median <= 0) return [];
	return daily
		.filter((d) => d[measure] >= 20 && d[measure] > median * 3)
		.map((d) => ({ day: d.day, value: d[measure], times: Math.round(d[measure] / median) }));
}

/** Rows as CSV, quoted where needed. */
export function toCsv(header: string[], rows: (string | number | null)[][]): string {
	const cell = (v: string | number | null) => {
		const s = v === null ? '' : String(v);
		return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
	};
	return [header, ...rows].map((r) => r.map(cell).join(',')).join('\n') + '\n';
}

/** Save a CSV file in the browser. */
export function downloadCsv(name: string, csv: string) {
	const url = URL.createObjectURL(new Blob(['﻿', csv], { type: 'text/csv;charset=utf-8' }));
	const a = document.createElement('a');
	a.href = url;
	a.download = name;
	document.body.appendChild(a);
	a.click();
	a.remove();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}

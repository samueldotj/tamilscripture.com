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
	/** accounts created (A8), merged in from analytics_accounts */
	signups: number;
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
	| 'sources'
	| 'langs'
	| 'audio_versions'
	| 'audio_time'
	| 'audio_chapters'
	| 'audio_sources'
	| 'audio_verses';
/** Over the last 24 hours, 7 days and 30 days. */
export interface Windows {
	day: number;
	week: number;
	month: number;
}
export interface Accounts {
	/** accounts that exist now */
	total: number;
	/** accounts created */
	signups: Windows;
	/** accounts that signed in at least once */
	signins: Windows;
	/** accounts with a session in use (the site refreshes it hourly while open) */
	active: Windows;
	peak_signups: { day: string; n: number } | null;
	/** the day with the most signed-in users (analytics member hash) */
	peak_members: { day: string; n: number } | null;
}
export interface PlanStat {
	/** built-in key ('bible-1y') or a community plan's id */
	key: string;
	title_ta: string | null;
	title_en: string | null;
	readers: number;
	/** joined in the range */
	started: number;
	/** ticked a passage in the last 7 days */
	active: number;
	passages: number;
}
export interface Plans {
	/** signed-in readers following at least one plan */
	readers: number;
	subscriptions: number;
	started: number;
	started_previous: number;
	active: number;
	/** most-followed first */
	plans: PlanStat[];
}
export interface Report {
	from: string;
	to: string;
	totals: Totals;
	/** the same length of time just before `from` */
	previous: Totals;
	daily: Day[];
	top: Partial<Record<Dimension, Row[]>>;
	/** referrers summed by source (A8): google, whatsapp, direct, … */
	sources: Row[];
	searches: Row[];
	searches_empty: Row[];
	accounts: Accounts | null;
	plans: Plans | null;
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

interface AccountsRpc extends Accounts {
	range: number;
	previous: number;
	daily: { day: string; n: number }[];
}

export async function loadReport(days: number): Promise<Report | null> {
	const to = istToday();
	const from = new Date(to);
	from.setDate(from.getDate() - (days - 1));
	const client = await sb();
	const range = { p_from: isoDay(from), p_to: isoDay(to) };
	// Accounts and plans are extras: until their migration is live the traffic
	// report still loads without them.
	const [main, acc, plans] = await Promise.all([
		client.rpc('analytics_report', range),
		client.rpc('analytics_accounts', range),
		client.rpc('analytics_plans', range)
	]);
	if (main.error) throw new Error(main.error.message);
	const report = (main.data as Report | null) ?? null;
	if (!report) return null;
	const a = acc.error ? null : ((acc.data as AccountsRpc | null) ?? null);
	const signups = new Map((a?.daily ?? []).map((d) => [d.day, d.n]));
	for (const d of report.daily) d.signups = signups.get(d.day) ?? 0;
	report.totals.signups = a?.range ?? 0;
	report.previous.signups = a?.previous ?? 0;
	report.sources ??= [];
	report.accounts = a;
	report.plans = plans.error ? null : ((plans.data as Plans | null) ?? null);
	return report;
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

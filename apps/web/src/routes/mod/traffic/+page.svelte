<script lang="ts">
	// Site traffic for reviewers and moderators (docs/feature_analytics.md §4).
	// Counts only: no visitor can be identified or followed across days.
	import { onMount } from 'svelte';
	import { findBook, findVersion, chapterUrl, manifest } from '$lib/content/manifest';
	import { downloadCsv, loadNow, loadReport, spikes, toCsv, type Dimension, type Measure, type Now, type Report, type Row } from '$lib/analytics/report';
	import { settings } from '$lib/settings/store.svelte';
	import { BUILTIN } from '$lib/plans/schedule';

	const ta = $derived(settings.value.uiLang === 'ta');
	const locale = $derived(ta ? 'ta-IN' : 'en-IN');
	let days = $state(30);
	let report = $state<Report | null>(null);
	let now = $state<Now | null>(null);
	let loading = $state(true);
	let error = $state('');
	let measure = $state<Measure>('views');
	let hover = $state<number | null>(null);

	async function load() {
		loading = true;
		error = '';
		try {
			[report, now] = await Promise.all([loadReport(days), loadNow().catch(() => null)]);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}
	async function refreshNow() {
		if (document.visibilityState !== 'visible') return;
		now = await loadNow().catch(() => now);
	}
	onMount(() => {
		load();
		const t = setInterval(refreshNow, 60_000);
		return () => clearInterval(t);
	});
	function setDays(n: number) {
		days = n;
		load();
	}

	const RANGES = [
		{ n: 7, ta: '7 நாள்', en: '7 days' },
		{ n: 30, ta: '30 நாள்', en: '30 days' },
		{ n: 90, ta: '90 நாள்', en: '90 days' },
		{ n: 365, ta: '1 ஆண்டு', en: '1 year' }
	];
	const MEASURES: { id: Measure; ta: string; en: string; hint_ta: string; hint_en: string }[] = [
		{ id: 'views', ta: 'பக்கப் பார்வைகள்', en: 'Page views', hint_ta: 'ஏற்றப்பட்ட ஒவ்வொரு பக்கமும்', hint_en: 'Every page loaded' },
		{ id: 'visitors', ta: 'வருகையாளர்கள்', en: 'Visitors', hint_ta: 'நாள்தோறும் எண்ணி, கூட்டியது', hint_en: 'Counted per day, summed' },
		{ id: 'unique_views', ta: 'தனிப் பார்வைகள்', en: 'Unique page views', hint_ta: 'ஒருவருக்கு ஒரு பக்கம் நாளுக்கு ஒருமுறை', hint_en: 'Each page once per visitor per day' },
		{ id: 'members', ta: 'உள்நுழைந்தவர்கள்', en: 'Signed-in users', hint_ta: 'நாள்தோறும் எண்ணி, கூட்டியது', hint_en: 'Counted per day, summed' },
		{ id: 'verse_clicks', ta: 'வசனத் தொடுதல்கள்', en: 'Verse clicks', hint_ta: 'வசன எண்ணைத் தொட்டுத் தேர்ந்தவை', hint_en: 'Verses selected by tapping the number' },
		{ id: 'signups', ta: 'புதிய கணக்குகள்', en: 'Sign-ups', hint_ta: 'உருவாக்கப்பட்ட கணக்குகள்', hint_en: 'Accounts created' }
	];
	// Audio Bible listening (docs/feature_analytics.md A7): a second row of tiles, also chart switches.
	const AUDIO: typeof MEASURES = [
		{ id: 'audio_starts', ta: 'அதிகார இயக்கங்கள்', en: 'Chapter plays', hint_ta: 'வாசகர் தொடங்கியவை, தானாகத் தொடர்ந்தவை', hint_en: 'Started by readers or by continuing' },
		{ id: 'listeners', ta: 'கேட்டவர்கள்', en: 'Listeners', hint_ta: 'நாள்தோறும் எண்ணி, கூட்டியது', hint_en: 'Counted per day, summed' },
		{ id: 'listen_seconds', ta: 'கேட்ட நேரம்', en: 'Listening time', hint_ta: 'உண்மையில் ஒலித்த நேரம்', hint_en: 'Time audio actually played' },
		{ id: 'audio_ends', ta: 'முழுதும் கேட்டவை', en: 'Chapters completed', hint_ta: 'முடிவு வரை கேட்ட அதிகாரங்கள்', hint_en: 'Heard to the end' }
	];
	// Sharing (A9): links from the reader's share menu and verses shared as an image.
	const SHARING: typeof MEASURES = [
		{ id: 'shares', ta: 'பகிர்வுகள்', en: 'Shares', hint_ta: 'இணைப்புகளும் படங்களும்', hint_en: 'Links and images' },
		{ id: 'sharers', ta: 'பகிர்ந்தவர்கள்', en: 'Sharers', hint_ta: 'நாள்தோறும் எண்ணி, கூட்டியது', hint_en: 'Counted per day, summed' },
		{ id: 'image_shares', ta: 'படமாகப் பகிர்ந்தவை', en: 'Shared as image', hint_ta: 'பதிவிறக்கம், பகிர்வு, நகல்', hint_en: 'Downloaded, sent or copied' }
	];
	const measureLabel = $derived([...MEASURES, ...AUDIO, ...SHARING].find((m) => m.id === measure)!);
	/** 3 h 20 m, 45 m, 30 s. */
	function duration(seconds: number) {
		if (seconds < 60) return `${seconds} s`;
		const minutes = Math.round(seconds / 60);
		const h = Math.floor(minutes / 60);
		const m = minutes % 60;
		if (h >= 100) return `${fmt.format(h)} h`;
		if (h) return m ? `${h} h ${m} m` : `${h} h`;
		return `${m} m`;
	}
	function tileValue(m: Measure, v: number) {
		return m === 'listen_seconds' ? duration(v) : compact.format(v);
	}
	/** Listening time is charted in minutes; everything else as counted. */
	const chartUnit = $derived(measure === 'listen_seconds' ? 60 : 1);
	const completion = $derived(report && report.totals.audio_starts ? Math.round((report.totals.audio_ends / report.totals.audio_starts) * 100) : null);
	const rangeLabel = $derived(RANGES.find((r) => r.n === days)!);

	const fmt = $derived(new Intl.NumberFormat(locale));
	const compact = $derived(new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }));
	const regionNames = $derived.by(() => {
		try {
			return new Intl.DisplayNames([ta ? 'ta' : 'en'], { type: 'region' });
		} catch {
			return null;
		}
	});
	function countryName(code: string) {
		if (!code || code === '?') return ta ? 'தெரியவில்லை' : 'Unknown';
		try {
			return regionNames?.of(code) ?? code;
		} catch {
			return code;
		}
	}
	function dayLabel(iso: string, long = false) {
		const d = new Date(`${iso}T00:00:00`);
		return d.toLocaleDateString(locale, long ? { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' } : { day: 'numeric', month: 'short' });
	}
	/** Change against the previous period of the same length. */
	function delta(m: Measure): { text: string; dir: 'up' | 'down' | 'flat' } | null {
		if (!report?.previous) return null;
		const cur = report.totals[m];
		const prev = report.previous[m];
		if (!prev && !cur) return null;
		if (!prev) return { text: ta ? 'புதியது' : 'new', dir: 'up' };
		const pct = Math.round(((cur - prev) / prev) * 100);
		if (pct === 0) return { text: '0%', dir: 'flat' };
		return { text: `${pct > 0 ? '+' : ''}${pct}%`, dir: pct > 0 ? 'up' : 'down' };
	}

	// ---- daily chart ----
	const W = 720;
	const H = 220;
	const PAD = { top: 12, right: 8, bottom: 26, left: 44 };
	const series = $derived((report?.daily ?? []).map((d) => ({ day: d.day, value: Math.round(d[measure] / chartUnit) })));
	const spikeDays = $derived(report ? spikes(report.daily, measure) : []);
	function niceStep(max: number) {
		if (max <= 4) return 1;
		const raw = max / 4;
		const p = 10 ** Math.floor(Math.log10(raw));
		const m = raw / p;
		return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
	}
	const scale = $derived.by(() => {
		const max = Math.max(1, ...series.map((s) => s.value));
		const step = niceStep(max);
		const top = Math.ceil(max / step) * step;
		const ticks: number[] = [];
		for (let t = 0; t <= top; t += step) ticks.push(t);
		return { top, ticks };
	});
	const band = $derived(series.length ? (W - PAD.left - PAD.right) / series.length : 0);
	const barW = $derived(Math.max(1, Math.min(24, band - 2)));
	const y = (v: number) => PAD.top + (H - PAD.top - PAD.bottom) * (1 - v / scale.top);
	/** A column with a 4px rounded data end, square at the baseline. */
	function column(i: number, v: number) {
		const x = PAD.left + i * band + (band - barW) / 2;
		const y0 = H - PAD.bottom;
		const y1 = y(v);
		const h = y0 - y1;
		if (h <= 0) return '';
		const r = Math.min(4, barW / 2, h);
		return `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + barW - r}Q${x + barW},${y1} ${x + barW},${y1 + r}V${y0}Z`;
	}
	const xLabels = $derived.by(() => {
		const n = series.length;
		if (!n) return [];
		const idx = n <= 7 ? series.map((_, i) => i) : [0, Math.round((n - 1) / 3), Math.round((2 * (n - 1)) / 3), n - 1];
		return idx.map((i) => ({ i, label: dayLabel(series[i].day) }));
	});

	// ---- books grid (A4) ----
	const bookViews = $derived(new Map((report?.top.books ?? []).map((r) => [r.key, r.n])));
	const bookMax = $derived(Math.max(1, ...bookViews.values()));
	/** Share of the busiest book, on a square-root scale so small books still show. */
	function shade(code: string) {
		const v = bookViews.get(code) ?? 0;
		return v ? 0.12 + 0.88 * Math.sqrt(v / bookMax) : 0;
	}
	const testaments = $derived([
		{ id: 'OT', ta: 'பழைய ஏற்பாடு', en: 'Old Testament', books: manifest.books.filter((b) => b.testament === 'OT') },
		{ id: 'NT', ta: 'புதிய ஏற்பாடு', en: 'New Testament', books: manifest.books.filter((b) => b.testament === 'NT') }
	]);

	// ---- ranked tables ----
	type Section = { id: Dimension | 'searches' | 'searches_empty'; ta: string; en: string; n_ta: string; n_en: string; u_ta: string; u_en: string; seconds?: boolean };
	const V = { n_ta: 'பார்வைகள்', n_en: 'Views', u_ta: 'வருகையாளர்', u_en: 'Visitors' };
	const A = { n_ta: 'இயக்கங்கள்', n_en: 'Plays', u_ta: 'கேட்டவர்', u_en: 'Listeners' };
	const S = { n_ta: 'பகிர்வுகள்', n_en: 'Shares', u_ta: 'பகிர்ந்தவர்', u_en: 'Sharers' };
	const SHARE_METHODS: Record<string, [string, string]> = {
		link: ['இணைப்பு: அதிகாரத்தில் வசனம்', 'Link: verse in its chapter'],
		large: ['இணைப்பு: பெரிய எழுத்து', 'Link: large text'],
		download: ['படம்: பதிவிறக்கம்', 'Image: downloaded'],
		sheet: ['படம்: பகிர்வுத் தாள்', 'Image: share sheet'],
		copy: ['படம்: நகல்', 'Image: copied']
	};
	const SHARE_TEMPLATES: Record<string, [string, string]> = {
		plate: ['தகடு', 'Plate'], margin: ['ஓரம்', 'Margin'], rules: ['கோடுகள்', 'Rules'], numeral: ['எண்', 'Numeral'], initial: ['முதலெழுத்து', 'Initial'], corner: ['மூலை', 'Corner'],
		square: ['சதுரம் 1080×1080', 'Square 1080×1080'], story: ['ஸ்டேட்டஸ் 1080×1920', 'Status 1080×1920'], landscape: ['கிடை 1200×630', 'Landscape 1200×630']
	};
	/** Referrers count landings: the first page of each visit. */
	const R = { n_ta: 'வருகைகள்', n_en: 'Visits', u_ta: 'வருகையாளர்', u_en: 'Visitors' };
	const SOURCE_NAMES: Record<string, [string, string]> = {
		play: ['அதிகாரத் தொடக்கத்திலிருந்து', 'From the start of a chapter'],
		verse: ['ஒரு வசனத்திலிருந்து', 'From a verse'],
		jump: ['கேட்கும்போது வசனத்துக்குத் தாவியது', 'Jumped to a verse while playing'],
		next: ['அடுத்த அதிகாரம் (தானாக அல்லது ⏭)', 'Next chapter (by itself or ⏭)']
	};
	function versionShort(code: string | null) {
		return (code && findVersion(code)?.short) || code || '?';
	}
	const SECTIONS: Section[] = [
		{ id: 'sources', ta: 'வருகையாளர் வந்த வழி', en: 'Where visitors come from', ...R },
		{ id: 'pages', ta: 'அதிகம் பார்க்கப்பட்ட பக்கங்கள்', en: 'Top pages', ...V },
		{ id: 'sections', ta: 'தளத்தின் பகுதிகள்', en: 'Parts of the site', ...V },
		{ id: 'chapters', ta: 'அதிகம் வாசிக்கப்பட்ட அதிகாரங்கள்', en: 'Most-read chapters', ...V },
		{ id: 'verses', ta: 'அதிகம் தொடப்பட்ட வசனங்கள்', en: 'Most-tapped verses', n_ta: 'தொடுதல்', n_en: 'Clicks', u_ta: 'வருகையாளர்', u_en: 'Visitors' },
		{ id: 'verse_books', ta: 'புத்தகவாரியாக வசனத் தொடுதல்கள்', en: 'Verse clicks by book', n_ta: 'தொடுதல்', n_en: 'Clicks', u_ta: 'வருகையாளர்', u_en: 'Visitors' },
		{ id: 'audio_chapters', ta: 'அதிகம் கேட்கப்பட்ட அதிகாரங்கள்', en: 'Most-played chapters', ...A },
		{ id: 'audio_versions', ta: 'பதிப்புவாரியாக ஒலி இயக்கங்கள்', en: 'Plays by version', ...A },
		{ id: 'audio_time', ta: 'பதிப்புவாரியாகக் கேட்ட நேரம்', en: 'Listening time by version', n_ta: 'நேரம்', n_en: 'Time', u_ta: 'கேட்டவர்', u_en: 'Listeners', seconds: true },
		{ id: 'audio_sources', ta: 'இயக்கம் தொடங்கிய விதம்', en: 'How playback started', n_ta: 'முறை', n_en: 'Times', u_ta: 'கேட்டவர்', u_en: 'Listeners' },
		{ id: 'audio_verses', ta: 'கேட்கத் தொடங்கிய வசனங்கள்', en: 'Verses played from', n_ta: 'முறை', n_en: 'Times', u_ta: 'கேட்டவர்', u_en: 'Listeners' },
		{ id: 'share_verses', ta: 'அதிகம் பகிரப்பட்ட வசனங்கள்', en: 'Most-shared verses', ...S },
		{ id: 'share_methods', ta: 'பகிர்ந்த விதம்', en: 'How verses were shared', ...S },
		{ id: 'share_templates', ta: 'பட வடிவங்கள்', en: 'Image templates', ...S },
		{ id: 'share_sizes', ta: 'பட அளவுகள்', en: 'Image sizes', ...S },
		{ id: 'searches', ta: 'தேடல் சொற்கள்', en: 'Search terms', n_ta: 'தேடல்கள்', n_en: 'Searches', u_ta: 'முடிவில்லை', u_en: 'No result' },
		{ id: 'searches_empty', ta: 'முடிவு இல்லாத தேடல்கள்', en: 'Searches with no result', n_ta: 'முடிவில்லை', n_en: 'No result', u_ta: 'மொத்தம்', u_en: 'All' },
		{ id: 'countries', ta: 'நாடுகள்', en: 'Countries', ...V },
		{ id: 'cities', ta: 'நகரங்கள்', en: 'Cities', ...V },
		{ id: 'devices', ta: 'சாதன வகை', en: 'Devices', ...V },
		{ id: 'screens', ta: 'திரைத் தெளிவுத்திறன்', en: 'Screen resolutions', ...V },
		{ id: 'os', ta: 'இயக்க முறைமைகள்', en: 'Operating systems', ...V },
		{ id: 'browsers', ta: 'உலாவிகள்', en: 'Browsers', ...V },
		{ id: 'referrers', ta: 'வந்த தளங்கள்', en: 'Referring sites', ...R },
		{ id: 'langs', ta: 'இடைமுக மொழி', en: 'Interface language', ...V }
	];
	const SECTION_NAMES: Record<string, [string, string]> = {
		reading: ['வாசிப்பு', 'Reading'],
		home: ['முகப்பு', 'Home'],
		atlas: ['வரைபடம்', 'Atlas'],
		dictionary: ['அகராதி', 'Dictionary'],
		places: ['இடங்கள்', 'Places'],
		people: ['நபர்கள்', 'People'],
		search: ['தேடல்', 'Search'],
		heatmap: ['வெப்ப வரைபடம்', 'Heatmap'],
		about: ['பற்றி', 'About'],
		moderation: ['மதிப்பாய்வு', 'Moderation'],
		account: ['கணக்கு', 'Account'],
		other: ['பிற', 'Other']
	};
	// Traffic sources (A8): analytics_source() in Postgres groups referrers into these.
	const ORIGIN_NAMES: Record<string, [string, string]> = {
		direct: ['நேரடியாக (வந்த தளம் இல்லை)', 'Direct (no referrer)'],
		google: ['Google', 'Google'],
		whatsapp: ['WhatsApp', 'WhatsApp'],
		facebook: ['Facebook', 'Facebook'],
		instagram: ['Instagram', 'Instagram'],
		youtube: ['YouTube', 'YouTube'],
		telegram: ['Telegram', 'Telegram'],
		x: ['X (Twitter)', 'X (Twitter)'],
		linkedin: ['LinkedIn', 'LinkedIn'],
		reddit: ['Reddit', 'Reddit'],
		bing: ['Bing', 'Bing'],
		duckduckgo: ['DuckDuckGo', 'DuckDuckGo'],
		search: ['பிற தேடுபொறிகள்', 'Other search engines'],
		email: ['மின்னஞ்சல்', 'Email'],
		ai: ['AI உதவியாளர்கள் (ChatGPT, Gemini…)', 'AI assistants (ChatGPT, Gemini…)'],
		other: ['பிற தளங்கள்', 'Other sites']
	};
	function referrerLabel(key: string) {
		if (key === '(direct)') return ORIGIN_NAMES.direct[ta ? 0 : 1];
		if (key.startsWith('utm:')) return `${key.slice(4)} ${ta ? '(இணைப்புக் குறி)' : '(link tag)'}`;
		return key;
	}
	function rowsFor(id: Section['id']): Row[] {
		if (!report) return [];
		if (id === 'sources') return report.sources ?? [];
		if (id === 'searches') return report.searches ?? [];
		if (id === 'searches_empty') return report.searches_empty ?? [];
		const rows = report.top[id] ?? [];
		return id === 'verse_books' || id === 'sections' ? rows.slice(0, 25) : rows;
	}
	function bookName(code: string) {
		const b = findBook(code);
		return b ? (ta ? b.name_ta : b.name_en) : code;
	}
	function rowLabel(id: Section['id'], r: Row): string {
		switch (id) {
			case 'countries':
				return countryName(r.key);
			case 'cities':
				return r.key === '?' ? (ta ? 'தெரியவில்லை' : 'Unknown') : `${r.key}, ${countryName(r.extra ?? '?')}`;
			case 'devices':
				return ({ mobile: ta ? 'கைபேசி' : 'Phone', tablet: ta ? 'டேப்லெட்' : 'Tablet', desktop: ta ? 'கணினி' : 'Desktop' } as Record<string, string>)[r.key] ?? r.key;
			case 'langs':
				return r.key === 'ta' ? 'தமிழ்' : r.key === 'en' ? 'English' : r.key;
			case 'sections':
				return SECTION_NAMES[r.key]?.[ta ? 0 : 1] ?? r.key;
			case 'sources':
				return ORIGIN_NAMES[r.key]?.[ta ? 0 : 1] ?? r.key;
			case 'referrers':
				return referrerLabel(r.key);
			case 'verse_books':
				return bookName(r.key);
			case 'audio_chapters': {
				const [code, ch] = r.key.split('.');
				return `${bookName(code)} ${ch} · ${versionShort(r.extra)}`;
			}
			case 'audio_versions':
			case 'audio_time':
				return findVersion(r.key)?.name ?? r.key;
			case 'audio_sources':
				return SOURCE_NAMES[r.key]?.[ta ? 0 : 1] ?? r.key;
			case 'audio_verses':
			case 'share_verses': {
				const [code, ch, v] = r.key.split('.');
				return `${bookName(code)} ${ch}:${v}`;
			}
			case 'share_methods':
				return SHARE_METHODS[r.key]?.[ta ? 0 : 1] ?? r.key;
			case 'share_templates':
			case 'share_sizes':
				return SHARE_TEMPLATES[r.key]?.[ta ? 0 : 1] ?? r.key;
			case 'chapters': {
				const [code, ch] = r.key.split('.');
				return `${bookName(code)} ${ch}`;
			}
			case 'verses': {
				const [code, ch, v] = r.key.split('.');
				return `${bookName(code)} ${ch}:${v}`;
			}
			default:
				return r.key;
		}
	}
	function rowHref(id: Section['id'], r: Row): string | null {
		const version = settings.value.version;
		if (id === 'pages') return r.key;
		if (id === 'audio_chapters' || id === 'audio_verses') {
			const [code, ch, v] = r.key.split('.');
			const b = findBook(code);
			const ver = id === 'audio_chapters' && r.extra && r.extra !== '?' ? r.extra.toLowerCase() : version;
			return b ? chapterUrl(ver, b, Number(ch), v) : null;
		}
		if (id === 'verses' || id === 'chapters' || id === 'share_verses') {
			const [code, ch, v] = r.key.split('.');
			const b = findBook(code);
			return b ? chapterUrl(version, b, Number(ch), v) : null;
		}
		if (id === 'searches' || id === 'searches_empty') return `/search?q=${encodeURIComponent(r.key)}`;
		return null;
	}
	function exportTable(sec: Section) {
		const rows = rowsFor(sec.id);
		downloadCsv(
			`traffic-${sec.id}-${report?.from}-${report?.to}.csv`,
			toCsv([sec.en, sec.seconds ? 'seconds' : sec.n_en, sec.u_en], rows.map((r) => [rowLabel(sec.id, r), r.n, r.u]))
		);
	}
	function exportDaily() {
		if (!report) return;
		downloadCsv(
			`traffic-daily-${report.from}-${report.to}.csv`,
			toCsv(
				['day', 'views', 'visitors', 'unique_views', 'signed_in', 'verse_clicks', 'sign_ups', 'audio_plays', 'listeners', 'listen_seconds', 'audio_completed', 'shares', 'sharers', 'image_shares'],
				report.daily.map((d) => [d.day, d.views, d.visitors, d.unique_views, d.members, d.verse_clicks, d.signups, d.audio_starts, d.listeners, d.listen_seconds, d.audio_ends, d.shares ?? 0, d.sharers ?? 0, d.image_shares ?? 0])
			)
		);
	}

	// ---- accounts and reading plans (A8) ----
	const WINDOWS = [
		{ id: 'day', ta: '24 மணி', en: 'Last day' },
		{ id: 'week', ta: '7 நாள்', en: 'Last week' },
		{ id: 'month', ta: '30 நாள்', en: 'Last month' }
	] as const;
	const ACCOUNT_ROWS = [
		{ id: 'signups', ta: 'பதிந்தவர்கள்', en: 'Signed up', hint_ta: 'புதிய கணக்குகள்', hint_en: 'Accounts created' },
		{ id: 'signins', ta: 'உள்நுழைந்தவர்கள்', en: 'Signed in', hint_ta: 'ஒரு முறையேனும் உள்நுழைந்த கணக்குகள்', hint_en: 'Accounts that signed in at least once' },
		{ id: 'active', ta: 'பயன்படுத்தியவர்கள்', en: 'Active while signed in', hint_ta: 'உள்நுழைந்த நிலையில் தளத்தைத் திறந்தவர்கள்', hint_en: 'Opened the site while signed in' }
	] as const;
	/** The range's busiest day for a daily measure. */
	function rangePeak(m: 'members' | 'signups') {
		let best: { day: string; n: number } | null = null;
		for (const d of report?.daily ?? []) if (d[m] > 0 && (!best || d[m] >= best.n)) best = { day: d.day, n: d[m] };
		return best;
	}
	const peaks = $derived(
		report?.accounts
			? [
					{ ta: 'அதிகம் பேர் பதிந்த நாள்', en: 'Peak sign-up day', ever: report.accounts.peak_signups, range: rangePeak('signups') },
					{ ta: 'அதிகம் பேர் உள்நுழைந்திருந்த நாள்', en: 'Peak day for signed-in users', ever: report.accounts.peak_members, range: rangePeak('members') }
				]
			: []
	);
	function planName(p: { key: string; title_ta: string | null; title_en: string | null }) {
		const b = BUILTIN.find((x) => x.id === p.key);
		if (b) return ta ? b.title.ta : b.title.en;
		return (ta ? p.title_ta || p.title_en : p.title_en || p.title_ta) || (ta ? 'நீக்கப்பட்ட திட்டம்' : 'Removed plan');
	}
	function exportPlans() {
		if (!report?.plans) return;
		downloadCsv(
			`traffic-plans-${report.from}-${report.to}.csv`,
			toCsv(['plan', 'readers', 'started_in_range', 'read_last_7_days', 'passages_read'], report.plans.plans.map((p) => [planName(p), p.readers, p.started, p.active, p.passages]))
		);
	}
</script>

<svelte:head><title>{ta ? 'வருகை' : 'Traffic'} · Tamil Scripture</title></svelte:head>

<div class="head">
	<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'தள வருகை' : 'Site traffic'}</h1>
	<div class="seg" role="group" aria-label={ta ? 'காலம்' : 'Range'}>
		{#each RANGES as r (r.n)}
			<button type="button" class:on={days === r.n} aria-pressed={days === r.n} onclick={() => setDays(r.n)} lang={ta ? 'ta' : 'en'}>{ta ? r.ta : r.en}</button>
		{/each}
	</div>
</div>

{#if error}
	<p class="err" role="alert">{error}</p>
{:else if !report && loading}
	<p class="muted">…</p>
{:else if !report}
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்தப் பக்கம் மதிப்பாய்வாளர்களுக்கு மட்டும்.' : 'This page is for reviewers and moderators.'}</p>
{:else}
	{#if now}
		<section class="card now" aria-live="polite">
			<div class="now-head">
				<span class="pulse" aria-hidden="true"></span>
				<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'இப்போது · கடந்த 30 நிமிடம்' : 'Now · last 30 minutes'}</h2>
			</div>
			<div class="now-body">
				<p class="now-n"><strong>{fmt.format(now.visitors)}</strong> <span lang={ta ? 'ta' : 'en'}>{ta ? 'வருகையாளர்கள்' : 'visitors'}</span> · <strong>{fmt.format(now.views)}</strong> <span lang={ta ? 'ta' : 'en'}>{ta ? 'பார்வைகள்' : 'views'}</span> · <strong>{fmt.format(now.verse_clicks)}</strong> <span lang={ta ? 'ta' : 'en'}>{ta ? 'தொடுதல்கள்' : 'verse clicks'}</span> · <strong>{fmt.format(now.listeners ?? 0)}</strong> <span lang={ta ? 'ta' : 'en'}>{ta ? 'கேட்கிறார்கள்' : 'listening'}</span></p>
				{#if now.listening?.length}
					<p class="now-c muted-n" lang={ta ? 'ta' : 'en'}>♪ {now.listening.map((l) => { const [code, ch] = l.key.split('.'); return `${bookName(code)} ${ch} · ${versionShort(l.extra)} (${fmt.format(l.n)})`; }).join(' · ')}</p>
				{/if}
				{#if now.pages.length}
					<ul class="now-list">
						{#each now.pages as p (p.key)}<li><a href={p.key}>{p.key}</a> <span class="muted-n">{fmt.format(p.n)}</span></li>{/each}
					</ul>
				{/if}
				{#if now.countries.length}
					<p class="now-c muted-n">{now.countries.map((c) => `${countryName(c.key)} ${fmt.format(c.n)}`).join(' · ')}</p>
				{/if}
			</div>
		</section>
	{/if}

	<div class="tiles" class:dim={loading}>
		{#each MEASURES.filter((m) => m.id !== 'signups' || report?.accounts) as m (m.id)}
			{@const d = delta(m.id)}
			<button type="button" class="tile" class:on={measure === m.id} aria-pressed={measure === m.id} onclick={() => (measure = m.id)}>
				<span class="label" lang={ta ? 'ta' : 'en'}>{ta ? m.ta : m.en}</span>
				<span class="value">{compact.format(report.totals[m.id])}</span>
				{#if d}
					<span class="delta {d.dir}" lang={ta ? 'ta' : 'en'}>{d.dir === 'up' ? '▲' : d.dir === 'down' ? '▼' : '■'} {d.text} <span class="vs">{ta ? `முந்தைய ${rangeLabel.ta} ஒப்பிட` : `vs previous ${rangeLabel.en}`}</span></span>
				{:else}
					<span class="hint" lang={ta ? 'ta' : 'en'}>{ta ? m.hint_ta : m.hint_en}</span>
				{/if}
			</button>
		{/each}
	</div>

	<h2 class="group kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'ஒலி வேதாகமம்' : 'Audio Bible'}</h2>
	<div class="tiles" class:dim={loading}>
		{#each AUDIO as m (m.id)}
			{@const d = delta(m.id)}
			<button type="button" class="tile" class:on={measure === m.id} aria-pressed={measure === m.id} onclick={() => (measure = m.id)}>
				<span class="label" lang={ta ? 'ta' : 'en'}>{ta ? m.ta : m.en}</span>
				<span class="value">{tileValue(m.id, report.totals[m.id])}</span>
				{#if m.id === 'audio_ends' && completion !== null}
					<span class="hint" lang={ta ? 'ta' : 'en'}>{ta ? `இயக்கங்களில் ${completion}%` : `${completion}% of plays`}</span>
				{:else if d}
					<span class="delta {d.dir}" lang={ta ? 'ta' : 'en'}>{d.dir === 'up' ? '▲' : d.dir === 'down' ? '▼' : '■'} {d.text} <span class="vs">{ta ? `முந்தைய ${rangeLabel.ta} ஒப்பிட` : `vs previous ${rangeLabel.en}`}</span></span>
				{:else}
					<span class="hint" lang={ta ? 'ta' : 'en'}>{ta ? m.hint_ta : m.hint_en}</span>
				{/if}
			</button>
		{/each}
	</div>

	<h2 class="group kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'பகிர்வு' : 'Sharing'}</h2>
	<div class="tiles" class:dim={loading}>
		{#each SHARING as m (m.id)}
			{@const d = delta(m.id)}
			<button type="button" class="tile" class:on={measure === m.id} aria-pressed={measure === m.id} onclick={() => (measure = m.id)}>
				<span class="label" lang={ta ? 'ta' : 'en'}>{ta ? m.ta : m.en}</span>
				<span class="value">{compact.format(report.totals[m.id] ?? 0)}</span>
				{#if d}
					<span class="delta {d.dir}" lang={ta ? 'ta' : 'en'}>{d.dir === 'up' ? '▲' : d.dir === 'down' ? '▼' : '■'} {d.text} <span class="vs">{ta ? `முந்தைய ${rangeLabel.ta} ஒப்பிட` : `vs previous ${rangeLabel.en}`}</span></span>
				{:else}
					<span class="hint" lang={ta ? 'ta' : 'en'}>{ta ? m.hint_ta : m.hint_en}</span>
				{/if}
			</button>
		{/each}
	</div>

	<section class="card chart" class:dim={loading}>
		<div class="sec-head">
			<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? measureLabel.ta : measureLabel.en} · {chartUnit === 60 ? (ta ? 'நிமிடங்கள், நாள்தோறும்' : 'minutes per day') : ta ? 'நாள்தோறும்' : 'per day'}</h2>
			<button type="button" class="csv" onclick={exportDaily}>CSV</button>
		</div>
		<div class="plot">
			<svg viewBox="0 0 {W} {H}" role="img" aria-label={`${ta ? measureLabel.ta : measureLabel.en}, ${ta ? 'நாள்தோறும்' : 'per day'}`}>
				{#each scale.ticks as t (t)}
					<line class="grid" x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} />
					<text class="tick" x={PAD.left - 8} y={y(t) + 4} text-anchor="end">{compact.format(t)}</text>
				{/each}
				{#each series as s, i (s.day)}
					<path class="col" class:hot={hover === i} d={column(i, s.value)} />
					<rect
						class="hit"
						x={PAD.left + i * band}
						y={PAD.top}
						width={band}
						height={H - PAD.top - PAD.bottom}
						role="presentation"
						onmouseenter={() => (hover = i)}
						onmouseleave={() => (hover = null)}
					/>
				{/each}
				{#each xLabels as l (l.i)}
					<text class="tick" x={PAD.left + l.i * band + band / 2} y={H - 8} text-anchor="middle">{l.label}</text>
				{/each}
			</svg>
			{#if hover !== null && series[hover]}
				<div class="tip" style="left: {((PAD.left + hover * band + band / 2) / W) * 100}%; top: {(y(series[hover].value) / H) * 100}%">
					<span class="tip-day">{dayLabel(series[hover].day, true)}</span>
					<strong>{chartUnit === 60 ? duration(series[hover].value * 60) : fmt.format(series[hover].value)}</strong>
				</div>
			{/if}
		</div>
		{#each spikeDays as sp (sp.day)}
			<p class="spike" lang={ta ? 'ta' : 'en'}>
				{ta
					? `வழக்கத்துக்கு மாறான உயர்வு: ${dayLabel(sp.day, true)} அன்று ${fmt.format(sp.value)}, வழக்கமான நாளைவிட ${sp.times} மடங்கு.`
					: `Unusual spike on ${dayLabel(sp.day, true)}: ${fmt.format(sp.value)}, ${sp.times}× a typical day.`}
			</p>
		{/each}
	</section>

	{#if report.accounts || report.plans}
		<div class="grid-2 people" class:dim={loading}>
			{#if report.accounts}
				{@const acc = report.accounts}
				<section class="card table">
					<div class="sec-head">
						<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'கணக்குகள்' : 'Accounts'}</h2>
						<span class="muted-n small-n" lang={ta ? 'ta' : 'en'}>{ta ? `மொத்தம் ${fmt.format(acc.total)}` : `${fmt.format(acc.total)} in all`}</span>
					</div>
					<table class="acc">
						<thead>
							<tr>
								<th scope="col" class="k"><span class="sr">{ta ? 'அளவு' : 'Measure'}</span></th>
								{#each WINDOWS as w (w.id)}<th scope="col" class="num" lang={ta ? 'ta' : 'en'}>{ta ? w.ta : w.en}</th>{/each}
							</tr>
						</thead>
						<tbody>
							{#each ACCOUNT_ROWS as r (r.id)}
								<tr>
									<th scope="row" class="rowh" lang={ta ? 'ta' : 'en'}>
										{ta ? r.ta : r.en}
										<span class="sub">{ta ? r.hint_ta : r.hint_en}</span>
									</th>
									{#each WINDOWS as w (w.id)}<td class="num">{fmt.format(acc[r.id][w.id])}</td>{/each}
								</tr>
							{/each}
						</tbody>
					</table>
					<dl class="peaks" lang={ta ? 'ta' : 'en'}>
						{#each peaks as p (p.en)}
							<div>
								<dt>{ta ? p.ta : p.en}</dt>
								<dd>
									{#if p.ever}<strong>{fmt.format(p.ever.n)}</strong> · {dayLabel(p.ever.day, true)}{:else}—{/if}
									{#if p.range && p.range.day !== p.ever?.day}
										<span class="muted-n"> · {ta ? `இந்தக் காலத்தில் ${dayLabel(p.range.day)} அன்று ${fmt.format(p.range.n)}` : `in this range ${fmt.format(p.range.n)} on ${dayLabel(p.range.day)}`}</span>
									{/if}
								</dd>
							</div>
						{/each}
					</dl>
				</section>
			{/if}
			{#if report.plans}
				{@const pl = report.plans}
				{@const top = pl.plans[0]}
				{@const max = Math.max(1, ...pl.plans.map((p) => p.readers))}
				<section class="card table">
					<div class="sec-head">
						<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'வாசிப்புத் திட்டங்கள்' : 'Reading plans'}</h2>
						{#if pl.plans.length}<button type="button" class="csv" onclick={exportPlans}>CSV</button>{/if}
					</div>
					<div class="minis" lang={ta ? 'ta' : 'en'}>
						<div><strong>{fmt.format(pl.readers)}</strong><span>{ta ? 'திட்டத்தில் உள்ள வாசகர்கள்' : 'readers on a plan'}</span></div>
						<div><strong>{fmt.format(pl.subscriptions)}</strong><span>{ta ? 'சேர்ந்த திட்டங்கள்' : 'plans joined'}</span></div>
						<div><strong>{fmt.format(pl.started)}</strong><span>{ta ? `${rangeLabel.ta} காலத்தில் தொடங்கியவை` : `started in ${rangeLabel.en}`}</span></div>
						<div><strong>{fmt.format(pl.active)}</strong><span>{ta ? '7 நாளில் வாசித்தவர்கள்' : 'read in the last 7 days'}</span></div>
					</div>
					{#if top}
						<p class="lead" lang={ta ? 'ta' : 'en'}>{ta ? 'அதிகம் பின்பற்றப்படுவது:' : 'Most followed:'} <strong>{planName(top)}</strong> · {ta ? `${fmt.format(top.readers)} வாசகர்கள்` : `${fmt.format(top.readers)} readers`}</p>
						<table>
							<thead>
								<tr>
									<th scope="col" class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'திட்டம்' : 'Plan'}</th>
									<th scope="col" class="num" lang={ta ? 'ta' : 'en'}>{ta ? 'வாசகர்' : 'Readers'}</th>
									<th scope="col" class="num" lang={ta ? 'ta' : 'en'}>{ta ? 'புதியவர்' : 'New'}</th>
									<th scope="col" class="num" lang={ta ? 'ta' : 'en'}>{ta ? '7 நாள்' : '7 days'}</th>
								</tr>
							</thead>
							<tbody>
								{#each pl.plans as p (p.key)}
									<tr>
										<td class="k">
											<span class="bar" style="width: {(p.readers / max) * 100}%" aria-hidden="true"></span>
											<span class="name">{planName(p)}</span>
										</td>
										<td class="num">{fmt.format(p.readers)}</td>
										<td class="num muted-n">{fmt.format(p.started)}</td>
										<td class="num muted-n">{fmt.format(p.active)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<p class="muted small" lang={ta ? 'ta' : 'en'}>{ta ? 'இதுவரை யாரும் திட்டத்தில் சேரவில்லை.' : 'Nobody has joined a plan yet.'}</p>
					{/if}
				</section>
			{/if}
		</div>
	{/if}

	<section class="card books" class:dim={loading}>
		<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? 'வாசிக்கப்பட்ட புத்தகங்கள் · அதிகாரப் பக்கப் பார்வைகள்' : 'Books read · chapter page views'}</h2>
		{#each testaments as t (t.id)}
			<h3 class="tname" lang={ta ? 'ta' : 'en'}>{ta ? t.ta : t.en}</h3>
			<div class="bgrid">
				{#each t.books as b (b.code)}
					{@const s = shade(b.code)}
					{@const v = bookViews.get(b.code) ?? 0}
					<a
						class="bcell"
						class:strong={s > 0.55}
						href={chapterUrl(settings.value.version, b)}
						style="--s: {s}"
						title={`${ta ? b.name_ta : b.name_en}: ${fmt.format(v)}`}
						aria-label={`${ta ? b.name_ta : b.name_en}: ${fmt.format(v)} ${ta ? 'பார்வைகள்' : 'views'}`}
					>{b.abbr_en[0] ?? b.code}</a>
				{/each}
			</div>
		{/each}
		<p class="legend muted-n" lang={ta ? 'ta' : 'en'}><span class="sw lo"></span>{ta ? 'குறைவு' : 'fewer'} <span class="sw hi"></span>{ta ? 'அதிகம்' : 'more'} · {ta ? 'வெற்றுக் கட்டம் = பார்வை இல்லை' : 'empty cell = no views'}</p>
	</section>

	<div class="grid-2" class:dim={loading}>
		{#each SECTIONS as sec (sec.id)}
			{@const rows = rowsFor(sec.id)}
			{@const max = Math.max(1, ...rows.map((r) => r.n))}
			<section class="card table">
				<div class="sec-head">
					<h2 class="kicker" lang={ta ? 'ta' : 'en'}>{ta ? sec.ta : sec.en}</h2>
					{#if rows.length}<button type="button" class="csv" onclick={() => exportTable(sec)}>CSV</button>{/if}
				</div>
				{#if rows.length}
					<table>
						<thead>
							<tr>
								<th scope="col" class="k" lang={ta ? 'ta' : 'en'}>{ta ? 'பெயர்' : 'Name'}</th>
								<th scope="col" class="num" lang={ta ? 'ta' : 'en'}>{ta ? sec.n_ta : sec.n_en}</th>
								<th scope="col" class="num" lang={ta ? 'ta' : 'en'}>{ta ? sec.u_ta : sec.u_en}</th>
							</tr>
						</thead>
						<tbody>
							{#each rows as r (r.key + (r.extra ?? ''))}
								{@const href = rowHref(sec.id, r)}
								<tr>
									<td class="k">
										<span class="bar" style="width: {(r.n / max) * 100}%" aria-hidden="true"></span>
										{#if href}<a {href} class="name">{rowLabel(sec.id, r)}</a>{:else}<span class="name">{rowLabel(sec.id, r)}</span>{/if}
									</td>
									<td class="num">{sec.seconds ? duration(r.n) : fmt.format(r.n)}</td>
									<td class="num muted-n">{fmt.format(r.u)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="muted small" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்தக் காலத்தில் தரவு இல்லை.' : 'Nothing in this range yet.'}</p>
				{/if}
			</section>
		{/each}
	</div>

	<p class="note" lang={ta ? 'ta' : 'en'}>
		{#if ta}
			கணக்குகள்: “உள்நுழைந்தவர்கள்” அந்தக் காலத்தில் ஒரு முறையேனும் உள்நுழைந்த கணக்குகள்; “பயன்படுத்தியவர்கள்” உள்நுழைந்த நிலையில் தளத்தைத் திறந்தவர்கள். வாசிப்புத் திட்டங்களில் உள்நுழைந்த வாசகர்கள் மட்டும் எண்ணப்படுவார்கள்; உள்நுழையாமல் சேர்ந்த திட்டம் அந்த உலாவியிலேயே இருக்கும். வந்த வழி ஒவ்வொரு வருகையின் முதல் பக்கத்தை மட்டும் பார்க்கிறது; WhatsApp போன்ற செயலிகள் பெரும்பாலும் வந்த தளத்தைச் சொல்வதில்லை, எனவே அவை “நேரடியாக” என எண்ணப்படலாம் — பகிரும் இணைப்பில் ?utm_source=whatsapp சேர்த்தால் சரியாக எண்ணப்படும். ஒலி வேதாகமம்: அதிகார இயக்கங்கள் வாசகர் தொடங்கியவையும் தானாகத் தொடர்ந்தவையும்; கேட்ட நேரம் ஒலி உண்மையில் ஒலித்த நேரம், பக்கம் பின்னணியில் இருந்தாலும் சேர்த்து. குக்கீகள் இல்லை; IP முகவரியோ பயனர் அடையாளமோ சேமிக்கப்படுவதில்லை. ஒரு வருகையாளர் அன்றைய நாளுக்கு மட்டும் செல்லும் மறைக்குறியீட்டால் எண்ணப்படுகிறார், எனவே பல நாள் காலத்தில் மீண்டும் வருபவர்கள் ஒவ்வொரு நாளும் தனியாக எண்ணப்படுவார்கள். இருப்பிடம் Vercel தரும் நகர அளவிலான மதிப்பீடு. “கண்காணிக்க வேண்டாம்” என்று கேட்கும் உலாவிகள் எண்ணப்படுவதில்லை. மூலத் தரவு 90 நாள், நாள்தோறும் சுருக்கிய எண்ணிக்கைகள் இரண்டு ஆண்டு வைக்கப்படுகின்றன.
		{:else}
			Accounts: “signed in” counts accounts that signed in at least once in the window; “active while signed in” counts accounts that opened the site while signed in. Reading plans count signed-in readers only; a plan joined while signed out stays in that browser. Where visitors come from looks at the first page of each visit only. Apps such as WhatsApp often send no referrer, so their visits can land under “Direct”; add ?utm_source=whatsapp to a shared link to count it. Audio Bible: chapter plays count chapters started by a reader and those that continued by themselves; listening time is the time audio actually played, including with the page in the background. Sharing counts shares that went through: a link from the reader's share menu (sent, or copied where the browser has no share sheet) or a verse image downloaded, sent or copied; a share sheet closed without sending is not counted. No cookies; no IP address or user id is stored. A visitor is counted with a code that lasts one day, so over a range a returning reader is counted once per day. Location is Vercel's city-level estimate. Browsers that ask not to be tracked are not counted. Raw events are kept for 90 days and daily summaries for two years.
		{/if}
	</p>
{/if}

<style>
	.head { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; }
	h1 { font-size: 1.5rem; margin: 0; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.seg { display: inline-flex; gap: 0.25rem; background: var(--surface-3); border-radius: 12px; padding: 4px; }
	.seg button { border: 0; border-radius: 9px; padding: 0.45rem 0.9rem; background: transparent; color: var(--muted); font: inherit; font-size: 0.85rem; font-weight: 600; cursor: pointer; min-height: 38px; }
	.seg button[lang='ta'] { font-family: var(--tamil); }
	.seg button.on { background: var(--surface); color: var(--ink); box-shadow: 0 1px 2px rgba(28, 26, 24, 0.1); }
	.dim { opacity: 0.55; transition: opacity 0.2s; }
	.err { color: var(--bad); }
	.muted { color: var(--muted); }
	.muted[lang='ta'] { font-family: var(--tamil); }
	.muted-n { color: var(--muted); }
	.small { font-size: 0.85rem; margin: 0; }
	.kicker[lang='ta'] { font-family: var(--tamil); letter-spacing: 0.02em; }
	.card { padding: 1rem 1.1rem; }
	.sec-head { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; margin: 0 0 0.6rem; }
	.sec-head h2 { margin: 0; }
	.csv { font: inherit; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; color: var(--muted); background: transparent; border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 0.15rem 0.55rem; cursor: pointer; }
	.csv:hover { color: var(--accent); border-color: var(--accent); }

	/* Now */
	.now { margin-bottom: 1rem; }
	.now-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
	.now-head h2 { margin: 0; }
	.pulse { width: 9px; height: 9px; border-radius: 999px; background: var(--good); box-shadow: 0 0 0 0 var(--good); animation: pulse 2s infinite; }
	@keyframes pulse { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--good) 60%, transparent); } 70% { box-shadow: 0 0 0 8px transparent; } 100% { box-shadow: 0 0 0 0 transparent; } }
	@media (prefers-reduced-motion: reduce) { .pulse { animation: none; } }
	.now-n { margin: 0 0 0.4rem; font-size: 0.95rem; }
	.now-n [lang='ta'] { font-family: var(--tamil); }
	.now-n strong { font-variant-numeric: tabular-nums; }
	.now-list { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.3rem 1rem; font-size: 0.85rem; }
	.now-list a { text-decoration: none; }
	.now-c { margin: 0.4rem 0 0; font-size: 0.8rem; }

	/* Stat tiles: each is also the switch for the chart below. */
	.group { margin: 0.4rem 0 0.6rem; }
	.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
	.tile { display: grid; gap: 0.2rem; text-align: left; padding: 0.9rem 1rem; border: var(--bw) solid var(--line-2); border-radius: var(--r-l); background: var(--surface); color: var(--ink); font: inherit; cursor: pointer; align-content: start; }
	.tile:hover { border-color: var(--accent); }
	.tile.on { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
	.tile .label { font-size: 0.8rem; font-weight: 600; color: var(--ink-2); }
	.tile .label[lang='ta'] { font-family: var(--tamil); font-size: 0.88rem; }
	.tile .value { font-size: 1.75rem; font-weight: 600; line-height: 1.15; font-family: var(--sans); }
	.tile .hint { font-size: 0.72rem; color: var(--muted); }
	.tile .hint[lang='ta'] { font-family: var(--tamil); }
	/* Up is good for every measure here, so direction picks the colour; the arrow
	   and the sign say it without colour. */
	.delta { font-size: 0.75rem; font-weight: 700; font-variant-numeric: tabular-nums; }
	.delta.up { color: var(--good); }
	.delta.down { color: var(--bad); }
	.delta.flat { color: var(--muted); }
	.delta .vs { font-weight: 400; color: var(--muted); }
	.delta[lang='ta'] .vs { font-family: var(--tamil); }

	/* Daily chart */
	.plot { position: relative; }
	.plot svg { display: block; width: 100%; height: auto; overflow: visible; }
	.grid { stroke: var(--line); stroke-width: 1; }
	.tick { fill: var(--muted); font: 11px var(--sans); font-variant-numeric: tabular-nums; }
	.col { fill: var(--accent); }
	.col.hot { fill: var(--accent-hover); }
	.hit { fill: transparent; }
	.tip { position: absolute; transform: translate(-50%, calc(-100% - 10px)); pointer-events: none; background: var(--surface); border: var(--bw) solid var(--line-2); border-radius: var(--r-s); box-shadow: var(--shadow); padding: 0.35rem 0.6rem; display: grid; gap: 0.05rem; white-space: nowrap; font-size: 0.8rem; z-index: 2; }
	.tip-day { color: var(--muted); font-size: 0.72rem; }
	.tip strong { font-variant-numeric: tabular-nums; }
	.spike { margin: 0.6rem 0 0; font-size: 0.82rem; color: var(--warn); }
	.spike[lang='ta'] { font-family: var(--tamil); }
	.spike::before { content: '⚠ '; }

	/* Books grid: one hue, light to dark by views. */
	.books { margin-top: 1rem; }
	.books h2 { margin: 0 0 0.4rem; }
	.tname { margin: 0.6rem 0 0.35rem; font-size: 0.75rem; font-weight: 700; color: var(--muted); letter-spacing: 0.04em; }
	.tname[lang='ta'] { font-family: var(--tamil); }
	.bgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(3.1rem, 1fr)); gap: 3px; }
	.bcell { display: grid; place-content: center; min-height: 2.1rem; border-radius: 5px; font-size: 0.72rem; font-weight: 600; text-decoration: none; color: var(--ink-2); border: 1px solid var(--line); background: color-mix(in srgb, var(--accent) calc(var(--s) * 100%), var(--surface)); }
	.bcell.strong { color: var(--on-accent); border-color: transparent; }
	.bcell:hover { outline: 2px solid var(--accent); outline-offset: 1px; }
	.legend { margin: 0.6rem 0 0; font-size: 0.75rem; display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
	.legend[lang='ta'] { font-family: var(--tamil); }
	.sw { width: 14px; height: 10px; border-radius: 3px; display: inline-block; border: 1px solid var(--line); }
	.sw.lo { background: color-mix(in srgb, var(--accent) 15%, var(--surface)); }
	.sw.hi { background: var(--accent); }

	/* Ranked tables */
	.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: 1rem; margin-top: 1rem; }
	.table { overflow-x: auto; }
	table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
	th { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); padding: 0 0 0.4rem; border-bottom: 1px solid var(--line); }
	th[lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.02em; font-size: 0.78rem; }
	th.k { text-align: left; }
	td { padding: 0.35rem 0; border-bottom: 1px solid var(--line); vertical-align: middle; }
	tr:last-child td { border-bottom: 0; }
	td.k { position: relative; padding-right: 0.8rem; max-width: 0; width: 100%; }
	/* The row's share as a quiet bar behind its name; the numbers carry the values. */
	.bar { position: absolute; left: 0; top: 50%; transform: translateY(-50%); height: 1.55rem; border-radius: 0 4px 4px 0; background: var(--accent-soft); z-index: 0; max-width: 100%; }
	.name { position: relative; z-index: 1; display: block; padding-left: 0.4rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ink); text-decoration: none; }
	a.name:hover { color: var(--accent); }
	.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; padding-left: 0.8rem; }
	/* Accounts and reading plans (A8) */
	.people { margin-top: 1rem; }
	.small-n { font-size: 0.78rem; }
	.small-n[lang='ta'] { font-family: var(--tamil); }
	.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
	th.rowh { text-align: left; font-size: 0.875rem; font-weight: 600; letter-spacing: 0; text-transform: none; color: var(--ink); padding: 0.4rem 0; }
	th.rowh[lang='ta'] { font-family: var(--tamil); }
	.acc thead th.num { white-space: normal; width: 4.2rem; }
	th.rowh .sub { display: block; font-size: 0.72rem; font-weight: 400; color: var(--muted); }
	tbody th { border-bottom: 1px solid var(--line); }
	tr:last-child th { border-bottom: 0; }
	.peaks { margin: 0.8rem 0 0; display: grid; gap: 0.5rem; font-size: 0.85rem; }
	.peaks[lang='ta'] { font-family: var(--tamil); }
	.peaks dt { font-size: 0.72rem; font-weight: 700; color: var(--muted); letter-spacing: 0.04em; }
	.peaks dd { margin: 0.1rem 0 0; font-variant-numeric: tabular-nums; }
	.minis { display: grid; grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr)); gap: 0.5rem; margin-bottom: 0.7rem; }
	.minis div { display: grid; gap: 0.05rem; padding: 0.5rem 0.65rem; border-radius: var(--r-s); background: var(--surface-3); }
	.minis strong { font-size: 1.25rem; font-weight: 600; font-variant-numeric: tabular-nums; }
	.minis span { font-size: 0.72rem; color: var(--muted); }
	.minis[lang='ta'] span { font-family: var(--tamil); }
	.lead { margin: 0 0 0.5rem; font-size: 0.85rem; }
	.lead[lang='ta'] { font-family: var(--tamil); }
	.note { margin: 1.4rem 0 0; font-size: 0.8rem; color: var(--muted); line-height: 1.6; max-width: 52rem; }
	.note[lang='ta'] { font-family: var(--tamil); }
</style>

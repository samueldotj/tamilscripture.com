<script lang="ts">
	import { chrome } from '$lib/chrome.svelte';
	import { afterNavigate, goto } from '$app/navigation';
	import Chapter from './Chapter.svelte';
	import DualChapter from './DualChapter.svelte';
	import ActionBar from './ActionBar.svelte';
	import Picker from './Picker.svelte';
	import XrefPanel from './XrefPanel.svelte';
	import NoteSheet from './NoteSheet.svelte';
	import BookRail from './BookRail.svelte';
	import ContextPanel from './ContextPanel.svelte';
	import type { TabId } from './ContextPanel.svelte';
	import StudyPanel from './StudyPanel.svelte';
	import NameCard from './NameCard.svelte';
	import { nameIndex, type NameHit } from './names';
	import { loadMapSvg, loadMentions } from '$lib/entities/load';
	import type { ChapterMentions } from '$lib/entities/types';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { loadXrefs } from '$lib/content/load';
	import { bookHeat, bucket } from '$lib/content/heat';
	import type { ChapterPageData } from '$lib/content/chapter-load';
	import type { XrefChapter } from '$lib/content/types';
	import { settings } from '$lib/settings/store.svelte';
	import { session } from '$lib/supabase/session.svelte';
	import { track } from '$lib/analytics/track';
	import { chapterHighlights, chapterNotes, recordVisit, setHighlight, removeHighlight, type Highlight, type HighlightColor, type Note } from '$lib/personal/repo';

	let { data }: { data: ChapterPageData } = $props();

	const primary = $derived(data.versions[0]);
	const dual = $derived(data.chapters.length > 1);
	const ui = $derived(settings.value.uiLang);
	const isTamil = $derived(ui === 'ta');
	const bookName = $derived(primary.lang === 'ta' ? data.book.name_ta : data.book.name_en);
	const altName = $derived(primary.lang === 'ta' ? data.book.name_en : data.book.name_ta);
	const uiBookName = $derived(isTamil ? data.book.name_ta : data.book.name_en);
	const versionPath = $derived(data.versions.map((v) => v.code.toLowerCase()).join('+'));
	const rangeLabel = $derived(
		data.range ? `${data.range.start}${data.range.end !== data.range.start ? `-${data.range.end}` : ''}` : ''
	);
	const title = $derived(`${bookName} ${data.chapter}${rangeLabel ? `:${rangeLabel}` : ''} · ${primary.short}`);

	// Description: the selected verses if any, else the chapter opening.
	const description = $derived.by(() => {
		const segs = data.chapters[0].blocks.flatMap((b) => (b.type === 'para' ? b.segments : []));
		const picked = data.range
			? segs.filter((s) => {
					const n = Number(s.id?.split('.')[2]);
					return n >= data.range!.start && n <= data.range!.end;
				})
			: segs;
		return picked.map((s) => s.text).join(' ').slice(0, 200);
	});

	const prev = $derived(data.chapters[0].prev);
	const next = $derived(data.chapters[0].next);
	function navUrl(ref: { book: string; chapter: number } | null) {
		if (!ref) return null;
		const b = findBook(ref.book);
		return b ? chapterUrl(versionPath, b, ref.chapter) : null;
	}
	const testamentName = $derived(
		data.book.testament === 'OT'
			? isTamil ? 'பழைய ஏற்பாடு' : 'Old Testament'
			: isTamil ? 'புதிய ஏற்பாடு' : 'New Testament'
	);

	// Selection: starts from the URL range (resolving bridges), then follows taps.
	function idsFromRange(): Set<string> {
		const ids = new Set<string>();
		if (!data.range) return ids;
		const bridges = data.chapters[0].bridges ?? {};
		for (let v = data.range.start; v <= data.range.end; v++) {
			const id = `${data.book.code}.${data.chapter}.${v}`;
			ids.add(bridges[id] ?? id);
		}
		return ids;
	}
	let selected = $state<Set<string>>(new Set());
	$effect(() => {
		// Reset when the passage changes.
		void data.canonical;
		selected = idsFromRange();
	});
	// Overlay sheet on screens without the desktop column: related verses
	// (‡ marker) or the study aids (Study chip, Study Bible format only).
	let sheet = $state<'related' | 'study' | null>(null);
	function toggle(id: string) {
		const s = new Set(selected);
		if (s.has(id)) s.delete(id); else {
			s.add(id);
			// A verse click, for the moderators' traffic page (docs/feature_analytics.md).
			track('verse', { verse: id, lang: settings.value.uiLang, user: session.user?.id });
		}
		selected = s;
		xrefOpen = null; // the context panel follows the selection again
	}
	function clearSelection() {
		selected = new Set();
		xrefOpen = null;
		if (fromText) getSelection()?.removeAllRanges();
		fromText = false;
	}

	// Drag-select (or long-press and drag on phones) across the text: the verses the browser's
	// own selection touches become the verse selection, so the colour bar appears while copy,
	// right-click and the phone's selection menu keep working untouched.
	let measure: HTMLDivElement | undefined = $state();
	let fromText = false;
	let pressed: Element | null = null;
	let pending = 0;
	function onPointerDown(e: PointerEvent) {
		pressed = e.target as Element | null;
	}
	function onSelectionChange() {
		clearTimeout(pending);
		pending = window.setTimeout(readSelection, 50);
	}
	function readSelection() {
		const sel = getSelection();
		const range = sel && sel.rangeCount && !sel.isCollapsed ? sel.getRangeAt(0) : null;
		if (!range || !measure || !measure.contains(range.commonAncestorContainer)) {
			// Clicking a colour or the note sheet collapses the text selection on some browsers;
			// the verses stay selected so the action still applies to them.
			if (fromText && !pressed?.closest('[role="toolbar"], [role="dialog"], aside.panel')) {
				fromText = false;
				selected = new Set();
			}
			return;
		}
		const ids = new Set<string>();
		for (const el of measure.querySelectorAll<HTMLElement>('[data-verse]')) {
			const id = el.dataset.verse;
			if (id && !isNaN(verseNum(id)) && range.intersectsNode(el)) ids.add(id);
		}
		if (!ids.size) {
			if (fromText) {
				fromText = false;
				selected = new Set();
			}
			return;
		}
		fromText = true;
		xrefOpen = null;
		if (ids.size !== selected.size || [...ids].some((id) => !selected.has(id))) selected = ids;
	}
	const verseNum = (id: string) => Number(id.split('.')[2]);
	const selectedNumbers = $derived([...selected].map(verseNum).filter((n) => !isNaN(n)).sort((a, b) => a - b));
	function rangeText(nums: number[]) {
		if (!nums.length) return '';
		const parts: string[] = [];
		let start = nums[0], last = nums[0];
		for (const n of nums.slice(1).concat(NaN)) {
			if (n === last + 1) { last = n; continue; }
			parts.push(start === last ? `${start}` : `${start}-${last}`);
			start = last = n;
		}
		return parts.join(',');
	}

	// Cross-references arrive with the page data (markers present at first
	// paint, hidden by CSS when off). If the toggle is switched on for a page
	// that was navigated to with it off, fetch them then.
	let fetched = $state<XrefChapter | null>(null);
	let xrefOpen = $state<string | null>(null);
	const xrefs = $derived(settings.value.xrefs ? (data.xrefs ?? fetched) : null);
	$effect(() => {
		const key = data.canonical;
		fetched = null;
		xrefOpen = null;
		sheet = null;
		if (data.xrefs || !settings.value.xrefs) return;
		let cancelled = false;
		loadXrefs(fetch, data.book.code, data.chapter)
			.then((x) => { if (!cancelled && key === data.canonical) fetched = x; })
			.catch(() => {});
		return () => { cancelled = true; };
	});
	function openXref(id: string) {
		xrefOpen = id;
		sheet = 'related';
	}

	// The context panel's aids: the chapter's places, persons and map. Fetched
	// after paint in every reading format — the panel offers them as tabs
	// whatever the format, so the Study Bible Show toggles govern the stacked
	// mobile sheet and the original-language forms, not whether a tab exists.
	const isStudy = $derived(settings.value.format === 'xref');
	const studyShow = $derived({ places: settings.value.places, persons: settings.value.persons, maps: settings.value.maps, language: settings.value.language });
	/** The panel is where the aids live, and there is no panel in compare view. */
	const panelWanted = $derived(!dual);
	/** The Show toggles belong to the Study Bible format and are only offered
	 *  there; in the other formats the aids are simply available, so a reader
	 *  is not left with a tab they cannot switch back on. */
	const aidShow = $derived(isStudy ? studyShow : { ...studyShow, places: true, persons: true, maps: true });
	let mentions = $state<ChapterMentions | null>(null);
	let mapSvg = $state<string | null>(null);
	let studyLoading = $state(false);
	/** How many distinct places and people the chapter names, for the tab counts. */
	const aidCounts = $derived.by(() => {
		const places = new Set<string>();
		const persons = new Set<string>();
		for (const v of mentions?.verses ?? []) {
			for (const id of v.places ?? []) if (mentions?.places[id]) places.add(id);
			for (const id of v.people ?? []) if ((mentions?.people ?? {})[id]) persons.add(id);
		}
		return { places: places.size, persons: persons.size };
	});
	/** The panel's tabs beside Related: whatever this chapter actually has. */
	const aids = $derived([
		...(mentions?.map ? [{ id: 'map' as const, ta: 'வரைபடம்', en: 'Map' }] : []),
		...(aidCounts.places ? [{ id: 'places' as const, ta: 'இடங்கள்', en: 'Places', n: aidCounts.places }] : []),
		...(aidCounts.persons ? [{ id: 'persons' as const, ta: 'நபர்கள்', en: 'Persons', n: aidCounts.persons }] : [])
	]);
	let panelTab = $state<TabId>('related');

	// Dictionary words (design 7A, task 7.15): people and places named in the
	// text carry a dotted underline when the setting is on; tapping one opens
	// its card in the context panel's அகராதி tab, or as a sheet on phones.
	const nameMap = $derived(settings.value.names && !dual ? nameIndex(mentions, primary) : null);
	let picked = $state<NameHit | null>(null);
	let nameSheet = $state(false);
	const pickedSummary = $derived(
		picked ? ((picked.kind === 'person' ? mentions?.people?.[picked.id] : mentions?.places[picked.id]) ?? null) : null
	);
	function pickName(hit: NameHit) {
		picked = hit;
		if (matchMedia('(min-width: 1180px)').matches) {
			panelTab = 'entry';
			nameSheet = false;
		} else {
			nameSheet = true;
		}
	}
	function closeName() {
		picked = null;
		nameSheet = false;
	}

	$effect(() => {
		const key = `${data.book.code}.${data.chapter}`;
		if (!panelWanted) return;
		mentions = null;
		picked = null;
		nameSheet = false;
		mapSvg = null;
		mapRequested = '';
		studyLoading = true;
		let cancelled = false;
		// The mentions are a couple of kilobytes; the chapter map is bigger and
		// most readers never open that tab, so it waits until one does.
		loadMentions(fetch, data.book.code, data.chapter)
			.then((m) => {
				if (!cancelled) mentions = m;
			})
			.catch(() => {})
			.finally(() => { if (!cancelled) studyLoading = false; });
		void key;
		return () => { cancelled = true; };
	});

	// The chapter map is fetched the first time the Map tab is opened, and kept
	// for as long as the chapter is on screen.
	let mapLoading = $state(false);
	// Which chapter's map has been asked for. A plain variable, not state: the
	// effect below would otherwise invalidate itself the moment it recorded the
	// request, cancel its own fetch on the re-run, and never finish.
	let mapRequested = '';
	$effect(() => {
		const key = `${data.book.code}.${data.chapter}`;
		if (panelTab !== 'map' || !mentions?.map || mapRequested === key) return;
		mapRequested = key;
		mapLoading = true;
		loadMapSvg(fetch, `${data.book.code}/${data.chapter}`)
			.then((svg) => {
				if (mapRequested === key) mapSvg = svg;
			})
			.catch(() => {})
			.finally(() => { if (mapRequested === key) mapLoading = false; });
	});

	// Desktop context panel: the verse whose ‡ was pressed, else the first
	// selected verse. Hidden by CSS below the wide breakpoint.
	const panelVerse = $derived(xrefOpen ?? [...selected].sort((a, b) => verseNum(a) - verseNum(b))[0] ?? null);
	const panelLabel = $derived(
		xrefOpen ? `${uiBookName} ${data.chapter}:${verseNum(xrefOpen)}`
		: selected.size ? `${uiBookName} ${data.chapter}:${rangeText(selectedNumbers)}`
		: ''
	);
	const panelTargets = $derived(panelVerse && xrefs ? xrefs[panelVerse] ?? [] : null);

	// Community heat (R-2.1, R-2.3): counts for tooltips and the action bar always;
	// the background tint only when the setting is on. Loaded after paint from
	// the hour-cached API; classes change background only, so no layout shift.
	let heatMap = $state<Map<number, { bucket: number; users: number }> | null>(null);
	$effect(() => {
		const key = data.canonical;
		heatMap = null;
		bookHeat(fetch, data.book.slug).then((h) => {
			if (key !== data.canonical) return;
			const ch = h[String(data.chapter)] ?? {};
			const allValues = Object.values(h).flatMap((c) => Object.values(c));
			const m = new Map<number, { bucket: number; users: number }>();
			for (const [v, users] of Object.entries(ch)) m.set(Number(v), { bucket: bucket(users, allValues), users });
			heatMap = m;
		});
	});
	const heatOverlay = $derived(settings.value.heat ? heatMap : heatMap && new Map([...heatMap].map(([k, v]) => [k, { bucket: 0, users: v.users }])));
	const selectedUsers = $derived.by(() => {
		if (!heatMap || !selected.size) return 0;
		return Math.max(0, ...[...selected].map((id) => heatMap!.get(verseNum(id))?.users ?? 0));
	});

	// Personal data (R-10.x): loaded after paint, only when signed in.
	let userHighlights = $state<Highlight[]>([]);
	let userNotes = $state<Note[]>([]);
	let noteOpen = $state<{ start: number; end: number; existing: Note | null } | null>(null);
	const highlightMap = $derived.by(() => {
		const m = new Map<string, string>();
		for (const h of userHighlights) for (let v = h.verse_start; v <= h.verse_end; v++) m.set(`${data.book.code}.${data.chapter}.${v}`, h.color);
		return m;
	});
	const notedSet = $derived.by(() => {
		const s = new Set<string>();
		for (const n of userNotes) for (let v = n.verse_start; v <= n.verse_end; v++) s.add(`${data.book.code}.${data.chapter}.${v}`);
		return s;
	});
	async function loadPersonal() {
		try {
			[userHighlights, userNotes] = await Promise.all([chapterHighlights(data.book.code, data.chapter), chapterNotes(data.book.code, data.chapter)]);
		} catch { /* offline or signed out */ }
	}
	$effect(() => {
		void data.canonical;
		userHighlights = [];
		userNotes = [];
		noteOpen = null;
		if (!session.ready || !session.signedIn) return;
		loadPersonal();
		recordVisit(data.book.code, data.chapter, primary.code, data.range).catch(() => {});
	});
	const currentColor = $derived.by(() => {
		if (!selected.size) return null;
		const colors = new Set([...selected].map((id) => highlightMap.get(id) ?? null));
		return colors.size === 1 ? ([...colors][0] as HighlightColor | null) : null;
	});
	async function applyHighlight(color: HighlightColor | null) {
		if (!selectedNumbers.length) return;
		try {
			if (color) await setHighlight(data.book.code, data.chapter, selectedNumbers, color);
			else await removeHighlight(data.book.code, data.chapter, selectedNumbers);
			await loadPersonal();
		} catch { /* surface later via toast */ }
	}
	function openNote(forId?: string) {
		const nums = forId ? [verseNum(forId)] : selectedNumbers;
		if (!nums.length) return;
		const start = nums[0], end = nums[nums.length - 1];
		const existing = userNotes.find((n) => n.verse_start <= start && n.verse_end >= start) ?? null;
		noteOpen = existing ? { start: existing.verse_start, end: existing.verse_end, existing } : { start, end, existing: null };
	}

	// Text size popover ("AA" in the toolbar), per the redesign's reader screen.
	let sizeOpen = $state(false);
	const fontSize = $derived(settings.value.fontSize);

	afterNavigate(() => {
		sizeOpen = false;
		if (!data.range) return;
		const first = document.getElementById(`${data.book.code}.${data.chapter}.${data.range.start}`)
			?? document.querySelector(`[data-verse="${[...idsFromRange()][0]}"]`);
		first?.scrollIntoView({ block: 'start' });
	});

	// Swipe between chapters on touch screens; arrow keys on desktop.
	let touchX = 0, touchY = 0;
	function touchStart(e: TouchEvent) { touchX = e.touches[0].clientX; touchY = e.touches[0].clientY; }
	function touchEnd(e: TouchEvent) {
		const dx = e.changedTouches[0].clientX - touchX;
		const dy = e.changedTouches[0].clientY - touchY;
		if (Math.abs(dx) > 70 && Math.abs(dy) < 50) {
			const target = dx < 0 ? navUrl(next) : navUrl(prev);
			if (target) goto(target);
		}
	}
	function onKey(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')) return;
		if (e.key === 'ArrowRight' && navUrl(next)) goto(navUrl(next)!);
		else if (e.key === 'ArrowLeft' && navUrl(prev)) goto(navUrl(prev)!);
		else if (e.key === 'Escape') {
			if (sizeOpen) sizeOpen = false;
			else if (sheet) sheet = null;
			else if (xrefOpen) xrefOpen = null;
			else if (selected.size) clearSelection();
		}
	}

	// Phones (design 10A): how far through the chapter, shown as a hairline while the bars are hidden.
	let progress = $state(0);
	function onScrollProgress() {
		const max = document.documentElement.scrollHeight - innerHeight;
		progress = max > 0 ? Math.min(1, Math.max(0, scrollY / max)) : 0;
	}
</script>

<svelte:window onkeydown={onKey} onscroll={onScrollProgress} />
<svelte:document onselectionchange={onSelectionChange} onpointerdowncapture={onPointerDown} />

<svelte:head>
	<title>{title} · Tamil Scripture</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={`https://www.tamilscripture.com${data.canonical}`} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:type" content="article" />
	<meta property="og:url" content={`https://www.tamilscripture.com${data.canonical}`} />
	{@html `<script type="application/ld+json">${JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'BreadcrumbList',
		itemListElement: [
			{ '@type': 'ListItem', position: 1, name: 'Bible', item: 'https://www.tamilscripture.com/' },
			{ '@type': 'ListItem', position: 2, name: data.book.name_en, item: `https://www.tamilscripture.com${chapterUrl(versionPath, data.book)}` },
			{ '@type': 'ListItem', position: 3, name: `${data.book.name_en} ${data.chapter}`, item: `https://www.tamilscripture.com${chapterUrl(versionPath, data.book, data.chapter)}` }
		]
	})}</script>`}
</svelte:head>

<!-- Three columns on wide screens for a single version (design 3A): book rail,
     reading column, context panel. Compare pages use the full width (design 3B). -->
<!-- svelte-ignore a11y_no_static_element_interactions -- swipe is a shortcut for the prev/next links below -->
<div class="reader" class:dual ontouchstart={touchStart} ontouchend={touchEnd}>
	{#if !dual}
		<aside class="rail">
			<BookRail versions={data.versions} book={data.book} chapter={data.chapter} lang={ui} />
		</aside>
	{/if}

	<div class="main">
		<div class="toolbar">
			<Picker versions={data.versions} book={data.book} chapter={data.chapter} lang={ui} />
			<div class="right">
				{#if aids.length}
					<button type="button" class="chip study-chip" onclick={() => (sheet = 'study')} aria-label={isTamil ? 'ஆய்வு: இடங்கள், நபர்கள், வரைபடம்' : 'Study: places, persons, map'}>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 19a2.5 2.5 0 0 1 2.5-2.5H20"/></svg>
						<span lang={isTamil ? 'ta' : 'en'}>{isTamil ? 'ஆய்வு' : 'Study'}</span>
					</button>
				{/if}
				<button type="button" class="chip aa" aria-label={isTamil ? 'எழுத்து அளவு' : 'Text size'} aria-expanded={sizeOpen} onclick={() => (sizeOpen = !sizeOpen)}>A<span>A</span></button>
				{#if navUrl(prev)}<a class="chip" href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முன்' : 'Prev'}</a>{/if}
				{#if navUrl(next)}<a class="chip primary" href={navUrl(next)} rel="next">{isTamil ? 'அடுத்து' : 'Next'} ›</a>{/if}
			</div>
		</div>

		<div class="measure" bind:this={measure}>
			<nav class="crumbs" aria-label="Breadcrumb">
				<a href="/">Bible</a>
				<span aria-hidden="true">›</span>
				<span>{testamentName}</span>
				<span aria-hidden="true">›</span>
				<a href={chapterUrl(versionPath, data.book)} lang={primary.lang}>{bookName}</a>
				<span aria-hidden="true">›</span>
				{#if data.range}
					<a href={chapterUrl(versionPath, data.book, data.chapter)}>{data.chapter}</a>
					<span aria-hidden="true">›</span>
					<span aria-current="page">{rangeLabel}</span>
				{:else}
					<span aria-current="page">{data.chapter}</span>
				{/if}
			</nav>

			<div class="titles">
				<h1 lang={primary.lang}>{bookName} {data.chapter}</h1>
				<span class="alt" lang={primary.lang === 'ta' ? 'en' : 'ta'}>{altName} {data.chapter}</span>
				{#if aids.length}
					<!-- On phones the toolbar gives way to the header pill and the thumb bar; Study stays here. -->
					<button type="button" class="chip study-chip m-study" onclick={() => (sheet = 'study')} aria-label={isTamil ? 'ஆய்வு: இடங்கள், நபர்கள், வரைபடம்' : 'Study: places, persons, map'}>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 19a2.5 2.5 0 0 1 2.5-2.5H20"/></svg>
						<span lang={isTamil ? 'ta' : 'en'}>{isTamil ? 'ஆய்வு' : 'Study'}</span>
					</button>
				{/if}
			</div>

			{#if !dual}
				<Chapter chapter={data.chapters[0]} lang={primary.lang} {selected} onselect={toggle} {xrefs} onxref={openXref} versionPath={primary.code.toLowerCase()} highlights={highlightMap} noted={notedSet} onnote={(id) => openNote(id)} heat={heatOverlay} names={nameMap} onname={pickName} />
			{:else}
				<DualChapter chapters={data.chapters} versions={data.versions} {selected} onselect={toggle} />
			{/if}

			<nav class="pager" aria-label={isTamil ? 'அதிகாரங்கள்' : 'Chapters'}>
				{#if navUrl(prev)}<a class="chip" href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முன்' : 'Previous'}</a>{:else}<span class="chip spacer" aria-hidden="true"></span>{/if}
				<a class="chip primary round list" href={chapterUrl(versionPath, data.book)} aria-label={isTamil ? `${bookName}: அதிகாரங்கள்` : `${bookName}: all chapters`} title={isTamil ? 'அதிகாரங்கள்' : 'All chapters'}>
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10" /></svg>
				</a>
				{#if navUrl(next)}<a class="chip" href={navUrl(next)} rel="next">{isTamil ? 'அடுத்து' : 'Next'} ›</a>{:else}<span class="chip spacer" aria-hidden="true"></span>{/if}
			</nav>

			<footer class="attribution">
				{#each data.versions as v (v.code)}
					<p><a href={v.source_url} rel="license">{v.attribution}</a></p>
				{/each}
			</footer>
		</div>
	</div>

	{#if !dual}
		<aside class="panel">
			<ContextPanel label={panelLabel} targets={panelTargets} xrefsEnabled={settings.value.xrefs} version={primary.code} lang={ui} {aids} bind:tab={panelTab} entry={picked && pickedSummary ? nameEntry : undefined}>
				{#snippet study(only)}
					<StudyPanel {mentions} {mapSvg} {selected} lang={ui} versionPath={primary.code.toLowerCase()} show={aidShow} loading={studyLoading || (only === 'map' && mapLoading)} {only} />
				{/snippet}
				{#snippet actions()}
					<ActionBar variant="panel" {selected} chapter={data.chapters[0]} book={data.book} {versionPath} versionShort={primary.short} lang={ui} signedIn={session.signedIn} {currentColor} communityUsers={selectedUsers} onclear={clearSelection} onhighlight={applyHighlight} onnote={() => openNote()} />
				{/snippet}
			</ContextPanel>
		</aside>
	{/if}
</div>

{#snippet nameEntry()}
	{#if picked && pickedSummary}
		<NameCard hit={picked} summary={pickedSummary} lang={ui} onclose={closeName} />
	{/if}
{/snippet}

<!-- A name tapped on a phone or tablet: its card as a half-sheet (design 7A). -->
{#if nameSheet && picked && pickedSummary}
	<button type="button" class="name-scrim" aria-label={isTamil ? 'மூடு' : 'Close'} onclick={closeName}></button>
	<div class="name-sheet" role="dialog" aria-label={isTamil ? 'அகராதி' : 'Dictionary'}>
		<span class="grip" aria-hidden="true"></span>
		<NameCard hit={picked} summary={pickedSummary} lang={ui} onclose={closeName} />
	</div>
{/if}

<!-- Overlays for screens without the context panel -->
<!-- Phones (design 10A): the thumb bar, and while reading only a floating AA and a progress hairline. -->
<div class="thumb" class:hidden={chrome.hidden || selected.size > 0}>
	{#if navUrl(prev)}<a class="tb" href={navUrl(prev)} rel="prev">‹ {isTamil ? 'முன்' : 'Prev'}</a>{:else}<span class="tb spacer" aria-hidden="true"></span>{/if}
	<button type="button" class="tb-aa" aria-label={isTamil ? 'எழுத்து அளவு' : 'Text size'} aria-expanded={sizeOpen} onclick={() => (sizeOpen = !sizeOpen)}>A<span>A</span></button>
	{#if navUrl(next)}<a class="tb" href={navUrl(next)} rel="next">{isTamil ? 'அடுத்து' : 'Next'} ›</a>{:else}<span class="tb spacer" aria-hidden="true"></span>{/if}
</div>
{#if chrome.hidden}
	<div class="progress" aria-hidden="true"><span style="width: {Math.round(progress * 100)}%"></span></div>
	<div class="fade" aria-hidden="true"></div>
	{#if selected.size === 0}
		<button type="button" class="float-aa" aria-label={isTamil ? 'எழுத்து அளவு' : 'Text size'} aria-expanded={sizeOpen} onclick={() => (sizeOpen = !sizeOpen)}>A<span>A</span></button>
	{/if}
{/if}

<div class="overlays" class:dual>
	<ActionBar {selected} chapter={data.chapters[0]} book={data.book} {versionPath} versionShort={primary.short} lang={ui} signedIn={session.signedIn} {currentColor} communityUsers={selectedUsers} onclear={clearSelection} onhighlight={applyHighlight} onnote={() => openNote()} />
	{#if sheet}
		<XrefPanel view={sheet} verseId={xrefOpen} targets={xrefOpen && xrefs ? xrefs[xrefOpen] ?? [] : null} version={primary.code} lang={ui} onclose={() => { sheet = null; xrefOpen = null; }}>
			{#snippet study()}
				<StudyPanel {mentions} {mapSvg} {selected} lang={ui} versionPath={primary.code.toLowerCase()} show={aidShow} loading={studyLoading} />
			{/snippet}
		</XrefPanel>
	{/if}
</div>

{#if sizeOpen}
	<div class="size card" role="dialog" aria-label={isTamil ? 'எழுத்து அளவு' : 'Text size'}>
		<div class="size-head">
			<strong><span lang="ta">எழுத்து அளவு</span> <span class="muted">· Text size</span></strong>
			<button type="button" class="x" onclick={() => (sizeOpen = false)} aria-label={isTamil ? 'மூடு' : 'Close'}>✕</button>
		</div>
		<div class="size-row">
			<button type="button" class="chip step" onclick={() => settings.update({ fontSize: Math.max(1, fontSize - 1) })} disabled={fontSize <= 1} aria-label={isTamil ? 'சிறிது' : 'Smaller'}>A −</button>
			<span class="sample" lang="ta" aria-live="polite">வசனம் <span class="n">{fontSize}/5</span></span>
			<button type="button" class="chip step" onclick={() => settings.update({ fontSize: Math.min(5, fontSize + 1) })} disabled={fontSize >= 5} aria-label={isTamil ? 'பெரிது' : 'Larger'}>A +</button>
		</div>
	</div>
{/if}

{#if noteOpen}
	<NoteSheet book={data.book.code} chapter={data.chapter} verseStart={noteOpen.start} verseEnd={noteOpen.end} existing={noteOpen.existing} lang={ui}
		label={`${bookName} ${data.chapter}:${noteOpen.start}${noteOpen.end !== noteOpen.start ? `-${noteOpen.end}` : ''}`}
		onclose={() => (noteOpen = null)} onsaved={() => loadPersonal()} />
{/if}

<style>
	/* Column frame. Single column by default; the rail joins at 960px and the
	   context panel at 1180px. Compare pages stay one centred column. */
	.reader { display: grid; grid-template-columns: minmax(0, 1fr); align-items: start; }
	.rail, .panel { display: none; }
	.main { width: 100%; max-width: 74rem; margin: 0 auto; padding: 1.5rem 1.5rem 4rem; }
	.measure { max-width: 40rem; margin: 0 auto; }
	.reader.dual .measure { max-width: none; }

	.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 0.6rem; padding: 0 0 1rem; margin: 0 0 1.5rem; border-bottom: var(--bw) solid var(--line); }
	.toolbar .right { display: flex; align-items: center; gap: 0.6rem; margin-left: auto; }
	.aa { font-family: var(--sans); font-weight: 700; color: var(--accent); gap: 0; }
	.study-chip [lang='ta'] { font-family: var(--tamil); }
	.aa span { font-size: 0.72em; }
	.crumbs { display: flex; gap: 0.5rem; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); margin: 0 0 1rem; }
	.crumbs a { color: var(--accent); font-weight: 600; text-decoration: none; }
	.crumbs a[lang='ta'] { font-family: var(--tamil); }
	.titles { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.4rem 0.9rem; margin: 0 0 0.6rem; }
	h1 { font-family: var(--sans); font-weight: 600; font-size: 2.2rem; margin: 0; line-height: 1.2; letter-spacing: -0.01em; }
	h1[lang='ta'] { font-family: var(--tamil); }
	.alt { font-size: 0.9rem; color: var(--muted); }
	.alt[lang='ta'] { font-family: var(--tamil); }
	.pager { display: flex; align-items: center; gap: 0.75rem; margin: 2.5rem 0 0; padding-top: 1rem; border-top: var(--bw) solid var(--line); }
	.pager .chip { flex: 1; min-height: 56px; border-radius: var(--r-l); font-size: 1rem; }
	.pager .list { flex: none; width: 56px; padding: 0; }
	.pager .spacer { visibility: hidden; }
	.attribution { margin-top: 2.5rem; font-size: 0.78rem; color: var(--muted); }
	.attribution a { color: inherit; }
	.attribution p { margin: 0.2rem 0; }

	.size { position: fixed; z-index: 16; left: 50%; bottom: max(1.25rem, env(safe-area-inset-bottom)); transform: translateX(-50%); width: min(24rem, calc(100vw - 2rem)); padding: 1.1rem; box-shadow: var(--shadow); border-radius: var(--r-2xl); border-color: var(--line-2); display: grid; gap: 0.9rem; }
	.size-head { display: flex; align-items: center; justify-content: space-between; font-size: 0.9rem; }
	.size-head [lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); font-weight: 400; }
	.x { border: 0; background: none; color: var(--muted); cursor: pointer; min-width: 40px; min-height: 40px; border-radius: 999px; }
	.x:hover { background: var(--surface-2); }
	.size-row { display: flex; gap: 0.75rem; align-items: stretch; }
	.step { width: 4.25rem; min-height: 56px; border-radius: 14px; font-family: var(--sans); font-size: 1.1rem; font-weight: 700; color: var(--ink-2); }
	.sample { flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.5rem; border: var(--bw) solid var(--accent); background: var(--accent-soft); border-radius: 14px; font-family: var(--tamil); font-size: 1.3rem; }
	.sample .n { font-family: var(--sans); font-size: 0.72rem; color: var(--muted); font-variant-numeric: tabular-nums; }

	.name-scrim { position: fixed; inset: 0; z-index: 21; border: 0; padding: 0; background: var(--scrim); cursor: default; }
	.name-sheet { position: fixed; z-index: 22; left: 50%; bottom: 0; transform: translateX(-50%); width: min(40rem, 100%); max-height: 70vh; overflow-y: auto; background: var(--surface); border: var(--bw) solid var(--line-2); border-bottom: 0; border-radius: 26px 26px 0 0; padding: 0.6rem 1.25rem calc(1.25rem + env(safe-area-inset-bottom)); box-shadow: var(--shadow-lg); }
	.name-sheet .grip { display: block; width: 44px; height: 5px; border-radius: 999px; background: var(--line-2); margin: 0 auto 0.6rem; }
	.thumb, .float-aa, .progress, .fade, .m-study { display: none; }
	@media (max-width: 720px) {
		/* Room at the end of the chapter for the thumb bar */
		.main { padding: 1.25rem 1rem 7.5rem; }
		.toolbar { display: none; }
		.m-study { display: inline-flex; margin-left: auto; align-self: center; }
		.thumb { display: flex; position: fixed; z-index: 14; left: 0; right: 0; bottom: 0; align-items: center; gap: 12px; padding: 14px 18px max(26px, env(safe-area-inset-bottom)); background: var(--bg); border-top: var(--bw) solid var(--line); transition: transform 0.22s ease; }
		.thumb.hidden { transform: translateY(100%); }
		.tb { flex: 1; height: 56px; border-radius: 16px; border: var(--bw) solid var(--line-2); background: var(--surface); display: flex; align-items: center; justify-content: center; gap: 8px; font-family: var(--tamil); font-size: 1rem; font-weight: 600; color: var(--ink); text-decoration: none; }
		.tb.spacer { visibility: hidden; }
		.tb-aa { width: 56px; height: 56px; flex: none; border-radius: 999px; border: 0; background: var(--accent); color: var(--on-accent); font-family: var(--sans); font-size: 15px; font-weight: 700; cursor: pointer; }
		.tb-aa span, .float-aa span { font-size: 11px; }
		.float-aa { display: flex; align-items: center; justify-content: center; position: fixed; z-index: 14; right: 22px; bottom: max(30px, env(safe-area-inset-bottom)); width: 52px; height: 52px; border-radius: 999px; background: color-mix(in srgb, var(--surface) 92%, transparent); border: var(--bw) solid var(--line-2); color: var(--accent); font-family: var(--sans); font-size: 15px; font-weight: 700; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); box-shadow: var(--shadow); cursor: pointer; }
		.progress { display: block; position: fixed; z-index: 14; top: max(4px, env(safe-area-inset-top)); left: 50%; transform: translateX(-50%); width: 120px; height: 3px; border-radius: 999px; background: var(--line-2); overflow: hidden; pointer-events: none; }
		.progress span { display: block; height: 100%; background: var(--accent); }
		.fade { display: block; position: fixed; z-index: 13; left: 0; right: 0; bottom: 0; height: 80px; background: linear-gradient(to top, var(--bg) 45%, transparent); pointer-events: none; }
	}
	@media (prefers-reduced-motion: reduce) {
		.thumb { transition: none; }
	}

	/* Rail joins. The side columns grow with the window up to 312px (rail) and
	   420px (panel); the clamps keep a 1180-1440px screen from squeezing the
	   reading column, which stays centred on its 40rem measure. */
	@media (min-width: 960px) {
		.reader:not(.dual) { grid-template-columns: clamp(16.75rem, 21vw, 19.5rem) minmax(0, 1fr); }
		.reader:not(.dual) .rail { display: block; position: sticky; top: var(--header-h, 0px); height: calc(100vh - var(--header-h, 0px)); }
		.reader:not(.dual) .main { max-width: none; padding: 1.5rem 2.5rem 4rem; }
		/* The rail covers book and chapter navigation */
		.reader:not(.dual) :global(.picker select.nav) { display: none; }
	}
	/* Context panel joins; the floating action bar, the overlay sheet and the Study chip step aside */
	@media (min-width: 1180px) {
		.reader:not(.dual) { grid-template-columns: clamp(16.75rem, 21vw, 19.5rem) minmax(0, 1fr) clamp(21.5rem, 27vw, 26.25rem); }
		.reader:not(.dual) .panel { display: block; position: sticky; top: var(--header-h, 0px); height: calc(100vh - var(--header-h, 0px)); overflow-y: auto; background: var(--surface); border-left: var(--bw) solid var(--line); scrollbar-width: thin; }
		.reader:not(.dual) .main { padding: 2rem 2.5rem 4rem; }
		.reader:not(.dual) .study-chip { display: none; }
		.overlays:not(.dual) { display: none; }
	}
</style>

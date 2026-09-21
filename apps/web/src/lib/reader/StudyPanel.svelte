<script lang="ts">
	// Study aids for the Study Bible format: the chapter map, the places and
	// the people named in the chapter, each behind its own Show toggle, with
	// the selected verse's names emphasised. Original-language forms appear
	// when the Language toggle is on.
	import type { ChapterMentions } from '$lib/entities/types';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { placeName } from '$lib/entities/load';
	import PanelMap from './PanelMap.svelte';

	let {
		mentions,
		mapSvg = null,
		selected = new Set<string>(),
		lang,
		versionPath,
		show,
		loading = false,
		only = null
	}: {
		mentions: ChapterMentions | null;
		mapSvg?: string | null;
		selected?: Set<string>;
		lang: 'ta' | 'en';
		versionPath: string;
		show: { places: boolean; persons: boolean; maps: boolean; language: boolean };
		loading?: boolean;
		/** Render one aid alone, without its heading — the context panel puts
		 *  each behind a tab and the tab is the heading. Null keeps all three
		 *  stacked, which is what the mobile sheet wants. */
		only?: 'map' | 'places' | 'persons' | null;
	} = $props();

	const ta = $derived(lang === 'ta');
	const book = $derived(mentions ? findBook(mentions.book) : undefined);

	type Row<T> = { id: string; p: T; verses: string[] };
	function rowsOf<T>(pick: (v: ChapterMentions['verses'][number]) => string[], table: Record<string, T>): Row<T>[] {
		if (!mentions) return [];
		const first = new Map<string, number>();
		const verses = new Map<string, string[]>();
		mentions.verses.forEach((v, i) => {
			for (const id of pick(v) ?? []) {
				if (!table[id]) continue;
				if (!first.has(id)) first.set(id, i);
				if (!verses.has(id)) verses.set(id, []);
				verses.get(id)!.push(v.verse);
			}
		});
		return [...first.entries()].sort((a, b) => a[1] - b[1]).map(([id]) => ({ id, p: table[id], verses: verses.get(id)! }));
	}
	const places = $derived(mentions ? rowsOf((v) => v.places, mentions.places) : []);
	const people = $derived(mentions ? rowsOf((v) => v.people, mentions.people ?? {}) : []);
	const selectedPlaces = $derived(new Set(mentions?.verses.filter((v) => selected.has(v.verse)).flatMap((v) => v.places) ?? []));
	const selectedPeople = $derived(new Set(mentions?.verses.filter((v) => selected.has(v.verse)).flatMap((v) => v.people ?? []) ?? []));
	// Selected verse's names first.
	const placeRows = $derived([...places].sort((a, b) => Number(selectedPlaces.has(b.id)) - Number(selectedPlaces.has(a.id))));
	const peopleRows = $derived([...people].sort((a, b) => Number(selectedPeople.has(b.id)) - Number(selectedPeople.has(a.id))));
	const nothing = $derived(!show.places && !show.persons && !show.maps);

	let mapEl: HTMLDivElement | undefined = $state();
	$effect(() => {
		if (!mapEl) return;
		for (const a of mapEl.querySelectorAll<SVGElement>('[data-place]')) {
			a.classList.toggle('selected', selectedPlaces.has(a.dataset.place ?? ''));
		}
	});

	function verseNo(v: string) {
		return v.split('.')[2];
	}
	function verseHref(v: string) {
		const [, ch, n] = v.split('.');
		return book ? chapterUrl(versionPath, book, Number(ch), n) : '#';
	}
	function label(p: { name_en: string; name_ta?: string | null; qualifier?: string | null }) {
		return placeName({ name_en: p.name_en, name_ta: p.name_ta ?? undefined, qualifier: p.qualifier ?? undefined }, lang);
	}
	function alt(p: { name_en: string; name_ta?: string | null }) {
		return ta ? p.name_en : (p.name_ta ?? '');
	}
	const exploreHref = $derived(mentions ? `/atlas/explore?chapter=${mentions.book}.${mentions.chapter}` : '/atlas/explore');
</script>

<div class="study" class:only={!!only} class:tall={only === 'map'}>
	{#if nothing && !only}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'அமைப்புகளில் “காட்டு” பகுதியில் இடங்கள், நபர்கள் அல்லது வரைபடங்களை இயக்குங்கள்.' : 'Turn on Places, Persons or Maps under Show in the settings.'}</p>
	{:else if loading}
		<p class="hint">…</p>
	{:else if !mentions}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த அதிகாரத்தில் பெயரிடப்பட்ட இடங்களோ நபர்களோ இல்லை.' : 'No places or people are named in this chapter.'}</p>
	{:else}
		{#if only === 'map' || (!only && show.maps)}
			<section>
				{#if !only}<h3 class="kicker"><span lang="ta">வரைபடம்</span> · Map</h3>{/if}
				{#if only === 'map' && mentions.map}
					<!-- Behind the tab the map has the panel's full height, which no
					     fixed landscape drawing fits: draw it live instead. -->
					<PanelMap {mentions} selected={selectedPlaces} {lang} />
				{:else if mapSvg}
					<div class="mapwrap" bind:this={mapEl}>{@html mapSvg}</div>
					<a class="chip explore" href={exploreHref}>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/></svg>
						<span lang="ta">வரைபடத்தில் காண்</span> · Explore map
					</a>
				{:else}
					<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த அதிகாரத்தின் இடங்களுக்கு அமைவிடம் அறியப்படவில்லை.' : 'None of this chapter’s places has a known location.'}</p>
				{/if}
			</section>
		{/if}

		{#if only === 'places' || (!only && show.places)}
			<section>
				{#if !only}<h3 class="kicker"><span lang="ta">இடங்கள்</span> · Places <span class="n">{placeRows.length}</span></h3>{/if}
				{#if placeRows.length}
					<ul class="list">
						{#each placeRows as r (r.id)}
							<li class:sel={selectedPlaces.has(r.id)}>
								<div class="row">
									<a class="name" href="/place/{r.id}" lang={ta && r.p.name_ta ? 'ta' : 'en'}>{label(r.p)}</a>
									<span class="alt" lang={ta ? 'en' : 'ta'}>{alt(r.p)}</span>
									{#if r.p.precision === 'unlocated'}<span class="tag" lang={ta ? 'ta' : 'en'}>{ta ? 'இடம் அறியப்படவில்லை' : 'location unknown'}</span>{/if}
								</div>
								<div class="verses">
									{#each r.verses.slice(0, 12) as v (v)}
										<a href={verseHref(v)} class:on={selected.has(v)} aria-label={ta ? `வசனம் ${verseNo(v)}` : `verse ${verseNo(v)}`}>{verseNo(v)}</a>
									{/each}
									{#if r.verses.length > 12}<span class="more">+{r.verses.length - 12}</span>{/if}
								</div>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த அதிகாரத்தில் இடங்கள் குறிப்பிடப்படவில்லை.' : 'No places are named in this chapter.'}</p>
				{/if}
			</section>
		{/if}

		{#if only === 'persons' || (!only && show.persons)}
			<section>
				{#if !only}<h3 class="kicker"><span lang="ta">நபர்கள்</span> · Persons <span class="n">{peopleRows.length}</span></h3>{/if}
				{#if peopleRows.length}
					<ul class="list">
						{#each peopleRows as r (r.id)}
							<li class:sel={selectedPeople.has(r.id)}>
								<div class="row">
									<a class="name" href="/person/{r.id}" lang={ta && r.p.name_ta ? 'ta' : 'en'}>{label(r.p)}</a>
									<span class="alt" lang={ta ? 'en' : 'ta'}>{alt(r.p)}</span>
									{#if r.p.gender === 'group'}<span class="tag" lang={ta ? 'ta' : 'en'}>{ta ? 'மக்கள் குழு' : 'people group'}</span>{/if}
								</div>
								{#if show.language && r.p.original}
									<p class="orig"><span lang={r.p.original.script}>{r.p.original.text}</span> <a class="strongs" href="/strongs/{r.p.original.strongs}">{r.p.original.strongs}</a>{#if r.p.original.translit} <span class="translit">{r.p.original.translit}</span>{/if}</p>
								{/if}
								{#if r.p.brief}<p class="brief">{r.p.brief}</p>{/if}
								<div class="verses">
									{#each r.verses.slice(0, 12) as v (v)}
										<a href={verseHref(v)} class:on={selected.has(v)} aria-label={ta ? `வசனம் ${verseNo(v)}` : `verse ${verseNo(v)}`}>{verseNo(v)}</a>
									{/each}
									{#if r.verses.length > 12}<span class="more">+{r.verses.length - 12}</span>{/if}
								</div>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த அதிகாரத்தில் பெயரிடப்பட்ட நபர்கள் இல்லை.' : 'No people are named in this chapter.'}</p>
				{/if}
			</section>
		{/if}

		{#if !only}
			<p class="credit">{#if show.maps || show.places}OpenBible.info · CC BY · Natural Earth{/if}{#if show.persons} · STEP Bible TIPNR · CC BY 4.0{/if}</p>
		{:else if only === 'persons'}
			<p class="credit">STEP Bible TIPNR · CC BY 4.0</p>
		{:else}
			<p class="credit">OpenBible.info · CC BY · Natural Earth</p>
		{/if}
	{/if}
</div>

<style>
	.study { display: grid; gap: 1.2rem; padding-top: 0.6rem; }
	/* Behind a tab there is one section, so it starts at the top. */
	.study.only { padding-top: 0; gap: 0.7rem; }
	section { display: grid; gap: 0.6rem; }
	.hint { color: var(--muted); line-height: 1.7; margin: 0.4rem 0 0; font-size: 0.95rem; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.mapwrap { aspect-ratio: 8 / 5; }
	/* Behind the Map tab the map takes the whole panel height. */
	.study.tall { display: flex; flex-direction: column; min-height: 0; }
	.study.tall section { display: flex; flex-direction: column; flex: 1; min-height: 0; }
	.mapwrap :global(svg) { width: 100%; height: 100%; }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.kicker .n { font-weight: 600; margin-left: 0.3rem; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; }
	.list li { padding: 0.6rem 0; border-top: 1px solid var(--line); display: grid; gap: 0.3rem; }
	.list li:first-child { border-top: 0; }
	.list li.sel { background: var(--hl); margin: 0 -0.6rem; padding-left: 0.6rem; padding-right: 0.6rem; border-radius: var(--r-s); }
	.row { display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; }
	.name { font-weight: 700; text-decoration: none; font-size: 1rem; }
	.name[lang='ta'] { font-family: var(--tamil); font-size: 1.05rem; }
	.alt { color: var(--muted); font-size: 0.8rem; }
	.alt[lang='ta'] { font-family: var(--tamil); }
	.tag { font-size: 0.72rem; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; }
	.tag[lang='ta'] { font-family: var(--tamil); }
	.orig { margin: 0; font-size: 0.95rem; display: flex; gap: 0.5rem; align-items: baseline; flex-wrap: wrap; }
	.orig [lang='he'] { font-size: 1.1rem; }
	.strongs { font-size: 0.7rem; color: var(--muted); letter-spacing: 0.04em; text-decoration: none; }
	a.strongs:hover { color: var(--accent); text-decoration: underline; }
	.translit { font-size: 0.82rem; color: var(--ink-2); font-style: italic; }
	.brief { margin: 0; font-size: 0.85rem; color: var(--ink-2); line-height: 1.5; }
	.verses { display: flex; flex-wrap: wrap; gap: 0.3rem; }
	.verses a { min-width: 1.9rem; text-align: center; padding: 0.1rem 0.4rem; border: 1px solid var(--line); border-radius: var(--r-s); text-decoration: none; font-size: 0.8rem; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--ink-2); background: var(--surface); }
	.verses a:hover, .verses a.on { border-color: var(--accent); color: var(--accent); }
	.verses .more { font-size: 0.78rem; color: var(--muted); align-self: center; }
	.explore { justify-self: start; }
	.credit { margin: 0; font-size: 0.72rem; color: var(--muted); }
</style>

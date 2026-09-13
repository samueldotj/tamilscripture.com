<script lang="ts">
	// Places named in the current chapter: the static chapter map with the
	// selected verse's places emphasised, then the list (design 3A / 04).
	import type { ChapterMentions } from '$lib/entities/types';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { placeName } from '$lib/entities/load';

	let {
		mentions,
		mapSvg = null,
		selected = new Set<string>(),
		lang,
		versionPath,
		loading = false
	}: {
		mentions: ChapterMentions | null;
		mapSvg?: string | null;
		/** selected verse ids */
		selected?: Set<string>;
		lang: 'ta' | 'en';
		versionPath: string;
		loading?: boolean;
	} = $props();

	const ta = $derived(lang === 'ta');
	const book = $derived(mentions ? findBook(mentions.book) : undefined);

	// Places in chapter order of first mention, with the verses that name them.
	const rows = $derived.by(() => {
		if (!mentions) return [];
		const first = new Map<string, number>();
		const verses = new Map<string, string[]>();
		mentions.verses.forEach((v, i) => {
			for (const id of v.places) {
				if (!first.has(id)) first.set(id, i);
				if (!verses.has(id)) verses.set(id, []);
				verses.get(id)!.push(v.verse);
			}
		});
		return [...first.entries()].sort((a, b) => a[1] - b[1]).map(([id]) => ({ id, p: mentions.places[id], verses: verses.get(id)! }));
	});
	const selectedIds = $derived(new Set(mentions?.verses.filter((v) => selected.has(v.verse)).flatMap((v) => v.places) ?? []));
	const selectedRows = $derived(rows.filter((r) => selectedIds.has(r.id)));

	let mapEl: HTMLDivElement | undefined = $state();
	$effect(() => {
		if (!mapEl) return;
		for (const a of mapEl.querySelectorAll<SVGElement>('[data-place]')) {
			a.classList.toggle('selected', selectedIds.has(a.dataset.place ?? ''));
		}
	});

	function verseNo(v: string) {
		return v.split('.')[2];
	}
	function verseHref(v: string) {
		const [, ch, n] = v.split('.');
		return book ? chapterUrl(versionPath, book, Number(ch), n) : '#';
	}
	function altName(p: { name_en: string; name_ta?: string | null; qualifier?: string | null }) {
		return ta ? p.name_en : (p.name_ta ?? '');
	}
	const exploreHref = $derived(mentions ? `/atlas/explore?chapter=${mentions.book}.${mentions.chapter}` : '/atlas/explore');
</script>

<div class="places">
	{#if loading}
		<p class="hint">…</p>
	{:else if !mentions || rows.length === 0}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த அதிகாரத்தில் இடங்கள் குறிப்பிடப்படவில்லை.' : 'No places are named in this chapter.'}</p>
	{:else}
		{#if mapSvg}
			<div class="mapwrap" bind:this={mapEl}>{@html mapSvg}</div>
		{/if}

		{#if selectedRows.length}
			<h3 class="kicker"><span lang="ta">தேர்ந்த வசனத்தில்</span> · In the selected verse</h3>
			<ul class="list em">
				{#each selectedRows as r (r.id)}
					<li>
						<a class="name" href="/place/{r.id}" lang={ta ? 'ta' : 'en'}>{placeName({ name_en: r.p.name_en, name_ta: r.p.name_ta ?? undefined, qualifier: r.p.qualifier ?? undefined }, lang)}</a>
						<span class="alt" lang={ta ? 'en' : 'ta'}>{altName(r.p)}</span>
					</li>
				{/each}
			</ul>
		{/if}

		<h3 class="kicker"><span lang="ta">இந்த அதிகாரத்தில்</span> · In this chapter <span class="n">{rows.length}</span></h3>
		<ul class="list">
			{#each rows as r (r.id)}
				<li class:sel={selectedIds.has(r.id)}>
					<div class="row">
						<a class="name" href="/place/{r.id}" lang={ta ? 'ta' : 'en'}>{placeName({ name_en: r.p.name_en, name_ta: r.p.name_ta ?? undefined, qualifier: r.p.qualifier ?? undefined }, lang)}</a>
						<span class="alt" lang={ta ? 'en' : 'ta'}>{altName(r.p)}</span>
						{#if r.p.precision === 'unlocated'}<span class="unloc" lang={ta ? 'ta' : 'en'}>{ta ? 'இடம் அறியப்படவில்லை' : 'location unknown'}</span>{/if}
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

		<a class="chip explore" href={exploreHref}>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/></svg>
			<span lang="ta">வரைபடத்தில் காண்</span> · Explore map
		</a>
		<p class="credit">OpenBible.info · CC BY · Natural Earth</p>
	{/if}
</div>

<style>
	.places { display: grid; gap: 0.9rem; padding-top: 0.6rem; }
	.hint { color: var(--muted); line-height: 1.7; margin: 0.8rem 0 0; font-size: 0.95rem; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.mapwrap { aspect-ratio: 8 / 5; }
	.mapwrap :global(svg) { width: 100%; height: 100%; }
	.kicker { margin: 0.4rem 0 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	.kicker .n { font-weight: 600; margin-left: 0.3rem; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; }
	.list li { padding: 0.6rem 0; border-top: 1px solid var(--line); display: grid; gap: 0.3rem; }
	.list li:first-child { border-top: 0; }
	.list li.sel { background: var(--hl); margin: 0 -0.6rem; padding-left: 0.6rem; padding-right: 0.6rem; border-radius: var(--r-s); }
	.list.em li .name { color: var(--amber); }
	.row { display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; }
	.name { font-weight: 700; text-decoration: none; font-size: 1rem; }
	.name[lang='ta'] { font-family: var(--tamil); font-size: 1.05rem; }
	.alt { color: var(--muted); font-size: 0.8rem; }
	.alt[lang='ta'] { font-family: var(--tamil); }
	.unloc { font-size: 0.72rem; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.5rem; }
	.unloc[lang='ta'] { font-family: var(--tamil); }
	.verses { display: flex; flex-wrap: wrap; gap: 0.3rem; }
	.verses a { min-width: 1.9rem; text-align: center; padding: 0.1rem 0.4rem; border: 1px solid var(--line); border-radius: var(--r-s); text-decoration: none; font-size: 0.8rem; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--ink-2); background: var(--surface); }
	.verses a:hover, .verses a.on { border-color: var(--accent); color: var(--accent); }
	.verses .more { font-size: 0.78rem; color: var(--muted); align-self: center; }
	.explore { justify-self: start; }
	.explore [lang='ta'] { font-family: var(--tamil); }
	.credit { margin: 0; font-size: 0.72rem; color: var(--muted); }
</style>

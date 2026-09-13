<script lang="ts">
	// People named in the current chapter (design: People tab), in order of
	// first mention, with the selected verse's people first.
	import type { ChapterMentions } from '$lib/entities/types';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import { placeName } from '$lib/entities/load';

	let {
		mentions,
		selected = new Set<string>(),
		lang,
		versionPath,
		loading = false
	}: {
		mentions: ChapterMentions | null;
		selected?: Set<string>;
		lang: 'ta' | 'en';
		versionPath: string;
		loading?: boolean;
	} = $props();

	const ta = $derived(lang === 'ta');
	const book = $derived(mentions ? findBook(mentions.book) : undefined);
	const rows = $derived.by(() => {
		if (!mentions?.people) return [];
		const first = new Map<string, number>();
		const verses = new Map<string, string[]>();
		mentions.verses.forEach((v, i) => {
			for (const id of v.people ?? []) {
				if (!first.has(id)) first.set(id, i);
				if (!verses.has(id)) verses.set(id, []);
				verses.get(id)!.push(v.verse);
			}
		});
		return [...first.entries()]
			.filter(([id]) => mentions.people[id])
			.sort((a, b) => a[1] - b[1])
			.map(([id]) => ({ id, p: mentions.people[id], verses: verses.get(id)! }));
	});
	const selectedIds = $derived(new Set(mentions?.verses.filter((v) => selected.has(v.verse)).flatMap((v) => v.people ?? []) ?? []));
	const ordered = $derived([...rows].sort((a, b) => Number(selectedIds.has(b.id)) - Number(selectedIds.has(a.id))));

	function verseNo(v: string) {
		return v.split('.')[2];
	}
	function verseHref(v: string) {
		const [, ch, n] = v.split('.');
		return book ? chapterUrl(versionPath, book, Number(ch), n) : '#';
	}
</script>

<div class="people">
	{#if loading}
		<p class="hint">…</p>
	{:else if rows.length === 0}
		<p class="hint" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த அதிகாரத்தில் பெயரிடப்பட்ட நபர்கள் இல்லை.' : 'No people are named in this chapter.'}</p>
	{:else}
		<h3 class="kicker"><span lang="ta">இந்த அதிகாரத்தில்</span> · In this chapter <span class="n">{rows.length}</span></h3>
		<ul class="list">
			{#each ordered as r (r.id)}
				<li class:sel={selectedIds.has(r.id)}>
					<div class="row">
						<a class="name" href="/person/{r.id}" lang={ta && r.p.name_ta ? 'ta' : 'en'}>{placeName({ name_en: r.p.name_en, name_ta: r.p.name_ta ?? undefined, qualifier: r.p.qualifier ?? undefined }, lang)}</a>
						<span class="alt" lang={ta ? 'en' : 'ta'}>{ta ? r.p.name_en : (r.p.name_ta ?? '')}</span>
						{#if r.p.gender === 'group'}<span class="tag" lang={ta ? 'ta' : 'en'}>{ta ? 'மக்கள் குழு' : 'people group'}</span>{/if}
					</div>
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
		<p class="credit">STEP Bible · TIPNR · CC BY 4.0</p>
	{/if}
</div>

<style>
	.people { display: grid; gap: 0.9rem; padding-top: 0.6rem; }
	.hint { color: var(--muted); line-height: 1.7; margin: 0.8rem 0 0; font-size: 0.95rem; }
	.hint[lang='ta'] { font-family: var(--tamil); }
	.kicker { margin: 0.4rem 0 0; }
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
	.brief { margin: 0; font-size: 0.85rem; color: var(--ink-2); line-height: 1.5; }
	.verses { display: flex; flex-wrap: wrap; gap: 0.3rem; }
	.verses a { min-width: 1.9rem; text-align: center; padding: 0.1rem 0.4rem; border: 1px solid var(--line); border-radius: var(--r-s); text-decoration: none; font-size: 0.8rem; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--ink-2); background: var(--surface); }
	.verses a:hover, .verses a.on { border-color: var(--accent); color: var(--accent); }
	.verses .more { font-size: 0.78rem; color: var(--muted); align-self: center; }
	.credit { margin: 0; font-size: 0.72rem; color: var(--muted); }
</style>

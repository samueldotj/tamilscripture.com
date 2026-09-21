<script lang="ts">
	// The dictionary card for a name tapped in the text (design 7A): headword,
	// the English and original-language forms, what it is, how often Scripture
	// names it, and the way on to the full entry and the dictionary article.
	// The desktop context panel shows it under its அகராதி tab; phones get it
	// as a half-sheet.
	import type { PersonSummary, PlaceSummary } from '$lib/entities/types';
	import type { NameHit } from './names';

	let {
		hit,
		summary,
		lang,
		onclose
	}: {
		hit: NameHit;
		summary: PersonSummary | PlaceSummary;
		lang: 'ta' | 'en';
		onclose?: () => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	const person = $derived(hit.kind === 'person' ? (summary as PersonSummary) : null);
	const place = $derived(hit.kind === 'place' ? (summary as PlaceSummary) : null);
	const head = $derived(ta && summary.name_ta ? summary.name_ta : summary.name_en);
	const headLang = $derived(ta && summary.name_ta ? 'ta' : 'en');
	const kind = $derived(hit.kind === 'person' ? (ta ? 'நபர்' : 'Person') : ta ? 'இடம்' : 'Place');
	const href = $derived(`/${hit.kind}/${hit.id}`);
</script>

<div class="card-name">
	<div class="top">
		<div>
			<p class="kicker"><span lang="ta">அகராதி</span> · Dictionary</p>
			<h3 lang={headLang}>{head}{#if summary.qualifier}<span class="q">{summary.qualifier}</span>{/if}</h3>
			<p class="alt">
				{#if headLang === 'ta'}<span lang="en">{summary.name_en}</span>{:else if summary.name_ta}<span lang="ta">{summary.name_ta}</span>{/if}
				{#if person?.original}<span class="orig" lang={person.original.script === 'he' ? 'he' : 'el'} dir={person.original.script === 'he' ? 'rtl' : 'ltr'}>{person.original.text}</span>{/if}
			</p>
		</div>
		{#if onclose}<button type="button" class="x" onclick={onclose} aria-label={ta ? 'மூடு' : 'Close'}>✕</button>{/if}
	</div>

	<div class="chips">
		<span class="chip-s" lang={ta ? 'ta' : 'en'}>{kind}</span>
		{#if person?.original?.strongs}<a class="chip-s link" href="/strongs/{person.original.strongs}" title={ta ? 'இச்சொல் வரும் எல்லா வசனங்களும்' : 'Every verse this word is used in'}>{person.original.script === 'he' ? (ta ? 'எபிரெயம்' : 'Hebrew') : ta ? 'கிரேக்கம்' : 'Greek'} · {person.original.strongs}</a>{/if}
		<span class="chip-s" lang={ta ? 'ta' : 'en'}>{summary.mentions.toLocaleString('en-IN')} {ta ? 'வசனங்கள்' : summary.mentions === 1 ? 'verse' : 'verses'}</span>
	</div>

	{#if person?.brief}
		<p class="brief" lang="en">{person.brief}</p>
	{:else if place?.type}
		<p class="brief" lang="en">{place.type}</p>
	{/if}

	<div class="actions">
		{#if summary.article}
			<a class="chip" href="/dictionary/{summary.article}" lang={ta ? 'ta' : 'en'}>{ta ? 'அகராதிக் கட்டுரை' : 'Dictionary article'}</a>
		{/if}
		<a class="chip primary" {href} lang={ta ? 'ta' : 'en'}>{ta ? 'முழு பதிவு ›' : 'Full entry ›'}</a>
	</div>
</div>

<style>
	.card-name { display: grid; gap: 0.8rem; }
	.top { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.6rem; }
	.kicker { margin: 0; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.04em; }
	h3 { margin: 0.2rem 0 0; font-size: 1.6rem; font-weight: 600; line-height: 1.2; }
	h3[lang='ta'] { font-family: var(--tamil); }
	.q { font-family: var(--sans); font-size: 0.7rem; color: var(--muted); margin-left: 0.3rem; vertical-align: super; }
	.alt { margin: 0.25rem 0 0; display: flex; flex-wrap: wrap; gap: 0.3rem 0.7rem; color: var(--ink-2); font-size: 0.9rem; }
	.alt [lang='ta'] { font-family: var(--tamil); }
	.orig { color: var(--accent); font-size: 1rem; }
	.x { border: 0; background: none; color: var(--muted); cursor: pointer; min-width: 40px; min-height: 40px; border-radius: 999px; flex: none; }
	.x:hover { background: var(--surface-2); }
	.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
	.chip-s { font-size: 0.75rem; font-weight: 600; color: var(--ink-2); border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 0.2rem 0.65rem; }
	.chip-s[lang='ta'] { font-family: var(--tamil); }
	.chip-s.link { color: var(--accent); text-decoration: none; }
	.chip-s.link:hover { border-color: var(--accent); }
	.brief { margin: 0; line-height: 1.6; color: var(--ink); }
	.actions { display: flex; flex-wrap: wrap; gap: 0.6rem; }
	.actions [lang='ta'] { font-family: var(--tamil); }
</style>

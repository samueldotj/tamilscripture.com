<script lang="ts">
	// One commentary unit's paragraphs (design 15B/15C): in Tamil where a draft
	// exists and the site is in Tamil, else the English original. The words a
	// note explains lead it in bold; references are links, those the import
	// resolved ("Mal. ii. 7") first, the rest by the site's own linkifier.
	import RefText from '$lib/refs/RefText.svelte';
	import { chapterUrl, findBook } from '$lib/content/manifest';
	import type { CommentaryParagraph, CommentaryUnit } from './load';

	let { unit, lang, versionPath, compact = false }: { unit: CommentaryUnit; lang: 'ta' | 'en'; versionPath: string; compact?: boolean } = $props();

	const showTa = $derived(lang === 'ta' && unit.paragraphs.some((p) => p.ta));

	function href(ref: string): string | null {
		const m = /^([1-4A-Z]{3})\.(\d+)(?:\.(\d+)(?:-(\d+)(?:\.\d+)?)?)?$/.exec(ref);
		const book = m && findBook(m[1]);
		if (!m || !book) return null;
		const verses = m[3] ? (m[4] && !ref.includes('-' + m[4] + '.') ? `${m[3]}-${m[4]}` : m[3]) : undefined;
		return chapterUrl(versionPath, book, Number(m[2]), verses);
	}

	/** The text cut at the references the import resolved: [text, href | null][] */
	function pieces(p: CommentaryParagraph, text: string): [string, string | null][] {
		const out: [string, string | null][] = [];
		let rest = text;
		for (const r of p.refs ?? []) {
			const i = rest.indexOf(r.text);
			const url = href(r.ref);
			if (i < 0 || !url) continue;
			if (i) out.push([rest.slice(0, i), null]);
			out.push([r.text, url]);
			rest = rest.slice(i + r.text.length);
		}
		if (rest) out.push([rest, null]);
		return out;
	}

	const paras = $derived(
		unit.paragraphs.map((p, i) => {
			const prev = unit.paragraphs[i - 1];
			const next = unit.paragraphs[i + 1];
			const ta = showTa && !!p.ta;
			return {
				p,
				ta,
				text: ta ? p.ta! : p.text,
				anchor: ta ? p.anchor_ta ?? p.anchor : p.anchor,
				// Early Church Fathers: the father's name before a quotation, the work after it.
				author: p.author && (!prev || prev.quote !== p.quote) ? p.author : null,
				work: p.work && (!next || next.quote !== p.quote) ? p.work : null
			};
		})
	);
</script>

<div class="cm" class:compact>
	{#each paras as x (x.p.id)}
		{#if x.author}
			<div class="who" lang="en">{x.author}{#if x.p.via}<span class="via">{` · ${x.p.via}`}</span>{/if}</div>
		{/if}
		{#if x.p.heading}
			<h4 lang={x.ta ? 'ta' : 'en'}>{x.text}</h4>
		{:else}
			<p lang={x.ta ? 'ta' : 'en'} class:ta={x.ta} class:foot={x.p.footnote} class:quoted={!!x.p.author}>
				{#if x.p.footnote && x.p.label}<span class="lab">{x.p.label}</span>{/if}
				{#if x.p.verse}<span class="v">{x.p.verse}</span>{/if}
				{#if x.anchor}<strong class="anchor">{#if x.p.label && !x.p.footnote}<span class="lab">{x.p.label}</span>{/if}{x.anchor}</strong>{' '}{/if}
				{#each pieces(x.p, x.text) as [t, url], k (k)}{#if url}<a class="ref-link" href={url}>{t}</a>{:else}<RefText text={t} version={versionPath} />{/if}{/each}
			</p>
		{/if}
		{#if x.work}
			<div class="work" lang="en">— {x.work}</div>
		{/if}
	{/each}
</div>

<style>
	.cm { display: grid; gap: 0.75rem; }
	.cm p { margin: 0; font-size: 1rem; line-height: 1.75; color: var(--ink-2); text-wrap: pretty; }
	.cm p.ta { font-family: var(--tamil); font-size: 1.06rem; line-height: 1.8; }
	.cm p[lang='en'] { font-family: var(--en); color: var(--ink-en); }
	.cm p.foot { font-size: 0.86rem; color: var(--muted); padding-left: 0.9rem; border-left: 2px solid var(--line-2); }
	.cm p.quoted { padding-left: 0.9rem; border-left: 2px solid var(--accent-soft); }
	.cm h4 { margin: 0.3rem 0 0; font-size: 0.95rem; font-weight: 700; color: var(--amber); }
	.cm h4[lang='ta'] { font-family: var(--tamil); }
	.anchor { font-weight: 700; color: var(--ink); }
	.anchor::after { content: ' —'; font-weight: 400; color: var(--muted); }
	.v { display: inline-block; min-width: 1.4em; font-family: var(--sans); font-size: 0.72em; font-weight: 700; color: var(--accent); vertical-align: 0.15em; margin-right: 0.3em; }
	.lab { font-family: var(--sans); font-size: 0.72em; font-weight: 700; color: var(--accent); margin-right: 0.35em; vertical-align: 0.15em; }
	.who { font-family: var(--sans); font-size: 0.82rem; font-weight: 700; color: var(--ink); margin-top: 0.35rem; }
	.via { font-weight: 400; color: var(--muted); }
	.work { font-family: var(--sans); font-size: 0.78rem; font-style: italic; color: var(--muted); margin-top: -0.35rem; }
	.ref-link { color: var(--accent); text-decoration: underline dotted; text-underline-offset: 0.2em; }
	.ref-link:hover { text-decoration-style: solid; }
	.compact p { font-size: 0.95rem; line-height: 1.7; }
	.compact p.ta { font-size: 1rem; }
</style>

<script lang="ts">
	// Cross references sample: the verses readers most often link to John 3:16,
	// the first two with their text.
	import { contentUrl, findBook, findVersion, manifest, verseUrl } from '$lib/content/manifest';
	import { verseLabel } from '$lib/entities/load';
	import Card from './Card.svelte';

	let { lang, versionPath }: { lang: 'ta' | 'en'; versionPath: string } = $props();
	const ta = $derived(lang === 'ta');
	const vp = $derived(versionPath.split('+')[0]);
	const version = $derived(findVersion(vp) ?? manifest.versions[0]);

	type Xref = { to: string; end?: string; votes: number };
	let refs = $state<Xref[]>([]);
	let texts = $state<Record<string, string>>({});

	async function load() {
		try {
			const chapter = (await (await fetch(contentUrl('xref/JHN/3.json'))).json()) as Record<string, Xref[]>;
			refs = [...(chapter['JHN.3.16'] ?? [])].sort((a, b) => b.votes - a.votes).slice(0, 7);
			const ids = refs.slice(0, 2).map((r) => r.to).join(',');
			if (ids) texts = await (await fetch(`/api/verses?${new URLSearchParams({ v: version.code, ids })}`)).json();
		} catch { /* offline */ }
	}
	function label(r: Xref): string {
		const base = verseLabel(r.to, lang);
		if (!r.end) return base;
		const [eb, ec, ev] = r.end.split('.'), [b, c] = r.to.split('.');
		return eb === b && ec === c ? `${base}–${ev}` : `${base} – ${verseLabel(r.end, lang)}`;
	}
	function href(r: Xref): string {
		const [code, c, v] = r.to.split('.');
		const e = r.end?.split('.');
		const range = e && e[0] === code && e[1] === c ? `${v}-${e[2]}` : v;
		return verseUrl(vp, findBook(code)!, Number(c), range);
	}
</script>

<Card ta="ஒத்த வசனங்கள்" en="Cross references" tag={ta ? 'யோவான் 3:16' : 'John 3:16'} href={verseUrl(vp, findBook('JHN')!, 3, '16')} cta={ta ? 'எல்லா ஒத்த வசனங்களும்' : 'All cross references'} {lang} onvisible={load}>
	{#if refs.length}
		{#each refs.slice(0, 2) as r (r.to)}
			<a class="ref" href={href(r)}>
				<span class="to" {lang}>{label(r)}</span>
				{#if texts[r.to]}<span class="text" lang={version.lang}>{texts[r.to]}</span>{/if}
			</a>
		{/each}
		<ul class="chips">
			{#each refs.slice(2) as r (r.to)}
				<li><a class="chip" href={href(r)} {lang}>{label(r)}</a></li>
			{/each}
		</ul>
	{:else}
		<div class="ph" aria-hidden="true"></div>
	{/if}
</Card>

<style>
	.ref { display: flex; flex-direction: column; gap: 0.35rem; padding: 0.85rem 1rem; border: var(--bw) solid var(--line); border-radius: var(--r-l); color: inherit; text-decoration: none; }
	.ref:hover { border-color: var(--accent); }
	.to { font-weight: 600; color: var(--accent); }
	.text { font-size: 0.95rem; line-height: 1.65; color: var(--ink-2); }
	[lang='ta'].to, [lang='ta'].text, .chip[lang='ta'] { font-family: var(--tamil); }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.chip { display: inline-flex; align-items: center; min-height: 40px; padding: 0 0.9rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font-size: 0.9rem; text-decoration: none; }
	.chip:hover { border-color: var(--accent); }
	.ph { min-height: 12rem; border-radius: var(--r-l); background: var(--surface-2); }
</style>

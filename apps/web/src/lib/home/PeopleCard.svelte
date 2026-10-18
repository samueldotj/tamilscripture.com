<script lang="ts">
	// Peoples sample: Abraham's page in small — his name in Hebrew, his family,
	// and a few more people to meet.
	import { loadPerson } from '$lib/entities/load';
	import type { Person } from '$lib/entities/types';
	import Card from './Card.svelte';

	let { lang }: { lang: 'ta' | 'en' } = $props();
	const ta = $derived(lang === 'ta');
	const MORE = [
		['moses', 'மோசே', 'Moses'], ['ruth', 'ரூத்', 'Ruth'], ['david', 'தாவீது', 'David'],
		['mary-mat-1-16', 'மரியாள்', 'Mary'], ['peter', 'பேதுரு', 'Peter'], ['paul', 'பவுல்', 'Paul']
	];

	let p = $state<Person | null>(null);
	const load = () => loadPerson(fetch, 'abraham').then((x) => (p = x)).catch(() => {});

	type Rel = { id: string; name_en: string; name_ta?: string };
	const name = (r: Rel) => (ta ? r.name_ta || r.name_en : r.name_en);
	const parent = $derived(p?.relations.parents?.[0] as Rel | undefined);
	const partners = $derived((p?.relations.partners ?? []).slice(0, 2) as Rel[]);
	const children = $derived((p?.relations.children ?? []).slice(0, 2) as Rel[]);
	const form = $derived(p?.forms[0]);
</script>

<Card ta="மக்கள்" en="Peoples" tag={ta ? 'நபர் · முற்பிதா' : 'Person · Patriarch'} href="/person/abraham" cta={ta ? 'ஆபிரகாமைப் பற்றி வாசிக்க' : 'Read about Abraham'} {lang} onvisible={load}>
	<div class="who">
		<div class="avatar" aria-hidden="true" lang="ta">ஆ</div>
		<div class="names">
			<div class="name"><span lang="ta">{p?.tamil_name?.label ?? 'ஆபிரகாம்'}</span> <span class="en">Abraham</span></div>
			{#if form}
				<div class="orig"><span lang={form.script} dir="rtl">{form.original}</span> · <a href="/strongs/{form.strongs}">{form.strongs}</a>{#if p} · <span {lang}>{ta ? `${p.verses.length} வசனங்கள்` : `${p.verses.length} verses`}</span>{/if}</div>
			{/if}
		</div>
	</div>

	{#if p && parent}
		<div class="tree" role="group" aria-label={ta ? 'குடும்பம்' : 'Family'}>
			<p class="kicker"><span lang="ta">குடும்பம்</span> · Family</p>
			<a class="chip" href="/person/{parent.id}" {lang}>{name(parent)}</a>
			<span class="v" aria-hidden="true"></span>
			<div class="gen">
				{#if partners[1]}<a class="chip" href="/person/{partners[1].id}" {lang}>{name(partners[1])}</a><span class="h" aria-hidden="true"></span>{/if}
				<span class="chip me" {lang}>{p.tamil_name && ta ? p.tamil_name.label : p.name_en}</span>
				{#if partners[0]}<span class="h" aria-hidden="true"></span><a class="chip" href="/person/{partners[0].id}" {lang}>{name(partners[0])}</a>{/if}
			</div>
			<span class="v" aria-hidden="true"></span>
			<div class="gen">
				{#each children as c (c.id)}<a class="chip" href="/person/{c.id}" {lang}>{name(c)}</a>{/each}
			</div>
		</div>
	{/if}

	<div class="more-people">
		<p class="kicker"><span lang="ta">மேலும் சந்திக்க</span> · More people</p>
		<ul class="chips">
			{#each MORE as [id, nta, nen] (id)}
				<li><a class="chip" href="/person/{id}" {lang}>{ta ? nta : nen}</a></li>
			{/each}
		</ul>
	</div>
</Card>

<style>
	.who { display: flex; gap: 1rem; align-items: center; }
	.avatar { flex: none; width: 3.6rem; height: 3.6rem; border-radius: 50%; background: var(--hl); color: var(--amber); display: flex; align-items: center; justify-content: center; font-family: var(--tamil); font-size: 1.6rem; font-weight: 600; }
	.names { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
	.name { font-size: 1.5rem; font-weight: 600; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.2rem 0.6rem; }
	.name [lang='ta'] { font-family: var(--tamil); }
	.name .en { font-size: 0.95rem; font-weight: 400; color: var(--ink-2); }
	.orig { font-size: 0.88rem; color: var(--ink-2); }
	.orig [lang='he'] { font-size: 1.05rem; }
	.orig [lang='ta'] { font-family: var(--tamil); }
	.kicker { margin: 0 0 0.6rem; align-self: flex-start; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; }
	.tree { display: flex; flex-direction: column; align-items: center; padding: 1rem 0.75rem; border-radius: var(--r-l); background: var(--surface-2); }
	.gen { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0.5rem; }
	.v { width: var(--bw); height: 1rem; background: var(--line-2); }
	.h { width: 0.9rem; height: var(--bw); background: var(--line-2); }
	.chips { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
	.chip { display: inline-flex; align-items: center; min-height: 40px; padding: 0 0.9rem; border: var(--bw) solid var(--line-2); border-radius: 999px; background: var(--surface); color: var(--ink); font-size: 0.9rem; text-decoration: none; }
	.chip[lang='ta'] { font-family: var(--tamil); }
	a.chip:hover { border-color: var(--accent); }
	.chip.me { border-color: var(--accent); background: var(--accent-soft); font-weight: 600; }
</style>

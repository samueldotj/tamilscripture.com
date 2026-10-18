<script lang="ts">
	// Reading plans sample: a reader with a plan sees today's passages to tick
	// off and their week; anyone else, the built-in plans to start one from.
	import { chapterUrl } from '$lib/content/manifest';
	import { session } from '$lib/supabase/session.svelte';
	import { plansStore } from '$lib/plans/store.svelte';
	import { addDays, BUILTIN, dayDone, key, passageLabel, schedule, stats, status, type Passage } from '$lib/plans/schedule';
	import { tone } from '$lib/plans/tone';
	import Card from './Card.svelte';

	let { lang, versionPath }: { lang: 'ta' | 'en'; versionPath: string } = $props();
	const ta = $derived(lang === 'ta');

	let seen = $state(false);
	$effect(() => {
		if (seen && session.ready) plansStore.load(session.signedIn);
	});

	const P = $derived(plansStore.ready ? plansStore.active : null);
	const m = $derived(P ? plansStore.progress(P.id) : null);
	const s = $derived(P ? schedule(P) : []);
	const st = $derived(P && m ? stats(P, m) : null);
	const stt = $derived(st ? status(st, lang) : null);
	const ti = $derived(P && st ? Math.max(0, Math.min(st.ti, P.days - 1)) : 0);
	const passages = $derived(s[ti] ?? []);
	const W = ['ஞா', 'தி', 'செ', 'பு', 'வி', 'வெ', 'ச'];
	const WE = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
	const week = $derived.by(() => {
		if (!P || !m || !st) return [];
		return Array.from({ length: 7 }, (_, i) => {
			const d = ti - 5 + i;
			const date = addDays(st.start, d);
			const state = d < 0 || d >= P.days ? 'out' : d === ti ? 'today' : dayDone(s[d], d, m.done) ? 'done' : d < ti ? 'missed' : 'ahead';
			return { d, day: (ta ? W : WE)[date.getDay()], n: date.getDate(), state };
		});
	});
	const readHref = (p: Passage) => {
		const u = p.units[0];
		return chapterUrl(versionPath, u.book, u.c, u.v ? `${u.v[0]}-${u.v[1]}` : undefined);
	};
	const R = 44, C = 2 * Math.PI * R;
</script>

<Card ta="வாசிப்புத் திட்டங்கள்" en="Reading plans" href={P ? '/plans' : '/plans/browse'} cta={P ? (ta ? 'இன்றைய வாசிப்பு' : "Today's reading") : ta ? 'ஒரு திட்டத்தைத் தொடங்க' : 'Start a plan'} {lang} onvisible={() => (seen = true)}>
	{#if P && m && st && stt}
		<div class="plan">
			<svg width="104" height="104" viewBox="0 0 104 104" role="img" aria-label="{st.pct}%">
				<circle cx="52" cy="52" r={R} fill="none" stroke="var(--surface-3)" stroke-width="10" />
				<circle cx="52" cy="52" r={R} fill="none" stroke="var(--accent)" stroke-width="10" stroke-linecap="round" stroke-dasharray="{(C * st.pct) / 100} {C}" transform="rotate(-90 52 52)" />
				<text x="52" y="50" text-anchor="middle" font-size="22" font-weight="700" fill="var(--ink)">{st.pct}%</text>
				<text x="52" y="68" text-anchor="middle" font-size="11" fill="var(--muted)">{ti + 1} / {P.days}</text>
			</svg>
			<div class="what">
				<div class="title" {lang}>{P.title[lang]}</div>
				<div class="sub" {lang}><span style:color={tone[stt.tone]}>{stt.text}</span>{#if st.streak > 1} · {ta ? `தொடர்ந்து ${st.streak} நாட்கள்` : `${st.streak}-day streak`}{/if}</div>
			</div>
		</div>
		<div class="week">
			{#each week as w (w.d)}
				<div class="d {w.state}"><span {lang}>{w.day}</span><b>{w.n}</b><i aria-hidden="true">{w.state === 'done' ? '✓' : w.state === 'today' ? '•' : ''}</i></div>
			{/each}
		</div>
		<div class="today">
			<p class="kicker"><span lang="ta">இன்று</span> · Today</p>
			{#each passages as p (p.ti)}
				{@const on = m.done.has(key(ti, p.ti))}
				<div class="row">
					<button type="button" class="box" class:on role="checkbox" aria-checked={on} aria-label={passageLabel(p.units, lang)} onclick={() => plansStore.setDone(P.id, [key(ti, p.ti)], !on)}>{on ? '✓' : ''}</button>
					<a href={readHref(p)} class:on {lang}>{passageLabel(p.units, lang)}</a>
				</div>
			{:else}
				<p class="rest" {lang}>{ta ? 'ஓய்வு நாள் — பின்தங்கியவற்றை வாசிக்க இதைப் பயன்படுத்துங்கள்.' : 'A spare day — use it to catch up.'}</p>
			{/each}
		</div>
	{:else}
		<p class="intro" {lang}>{ta ? 'ஒவ்வொரு நாளும் சில அதிகாரங்கள். நீங்கள் வாசித்ததைக் குறித்துக்கொள்ளுங்கள்; பின்தங்கினால் தளம் நினைவூட்டும்.' : 'A few chapters a day. Tick off what you read, and see when you fall behind.'}</p>
		<ul class="plans">
			{#each BUILTIN.slice(0, 3) as p (p.id)}
				<li>
					<a href="/plans/browse">
						<span class="pt" {lang}>{p.title[lang]}</span>
						<span class="pb" {lang}>{p.blurb[lang]}</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</Card>

<style>
	.plan { display: flex; gap: 1.2rem; align-items: center; flex-wrap: wrap; }
	.plan text { font-family: var(--sans); }
	.what { flex: 1 1 10rem; min-width: 0; display: flex; flex-direction: column; gap: 0.25rem; }
	.title { font-size: 1.3rem; font-weight: 600; line-height: 1.3; }
	.sub { font-size: 0.88rem; color: var(--ink-2); }
	[lang='ta'].title, [lang='ta'].sub, [lang='ta'].intro, [lang='ta'].pt, [lang='ta'].pb, [lang='ta'].rest, .row a[lang='ta'], .d span[lang='ta'] { font-family: var(--tamil); }
	.week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 0.35rem; }
	.d { display: flex; flex-direction: column; align-items: center; gap: 0.1rem; padding: 0.45rem 0; border-radius: var(--r); background: var(--surface-2); color: var(--muted); font-size: 0.75rem; }
	.d b { font-size: 1rem; }
	.d i { font-style: normal; height: 0.9rem; font-size: 0.7rem; }
	.d.done { background: var(--good-soft); color: var(--good); }
	.d.today { background: var(--accent); color: var(--on-accent); }
	.d.missed { background: var(--bad-soft); color: var(--bad); }
	.d.out { opacity: 0.4; }
	.today { display: flex; flex-direction: column; }
	.kicker { margin: 0 0 0.3rem; }
	.kicker [lang='ta'] { font-family: var(--tamil); letter-spacing: 0.03em; text-transform: none; }
	.row { display: flex; align-items: center; gap: 0.8rem; min-height: 48px; border-bottom: var(--bw) solid var(--line); }
	.row:last-child { border-bottom: 0; }
	.box { flex: none; width: 26px; height: 26px; border-radius: 7px; border: var(--bw) solid var(--line-2); background: var(--surface); color: var(--on-accent); font-weight: 700; cursor: pointer; padding: 0; }
	.box.on { background: var(--accent); border-color: var(--accent); }
	.row a { color: var(--ink); text-decoration: none; }
	.row a.on { color: var(--muted); text-decoration: line-through; }
	.rest { margin: 0; color: var(--ink-2); }
	.intro { margin: 0; color: var(--ink-2); line-height: 1.65; }
	.plans { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
	.plans a { display: flex; flex-direction: column; gap: 0.15rem; padding: 0.8rem 1rem; border: var(--bw) solid var(--line); border-radius: var(--r-l); color: inherit; text-decoration: none; }
	.plans a:hover { border-color: var(--accent); }
	.pt { font-weight: 600; }
	.pb { font-size: 0.88rem; color: var(--ink-2); line-height: 1.55; }
</style>

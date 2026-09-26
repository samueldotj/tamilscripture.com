<script lang="ts">
	// Today (design 14A): the day's passages for the chosen plan, ticked off one
	// by one or all at once, then the days to catch up and the days ahead.
	import { settings } from '$lib/settings/store.svelte';
	import { chapterUrl } from '$lib/content/manifest';
	import { plansStore } from '$lib/plans/store.svelte';
	import PlanChips from '$lib/plans/PlanChips.svelte';
	import { tone } from '$lib/plans/tone';
	import {
		addDays, dayKeys, dayLabel, key, passageLabel, schedule, shortDate, stats, status, weekDate, type Passage
	} from '$lib/plans/schedule';

	const lang = $derived(settings.value.uiLang);
	const ta = $derived(lang === 'ta');
	const other = $derived(ta ? 'en' : 'ta');

	const P = $derived(plansStore.active);
	const m = $derived(P ? plansStore.progress(P.id) : null);
	const s = $derived(P ? schedule(P) : []);
	const st = $derived(P && m ? stats(P, m) : null);
	const stt = $derived(st ? status(st, lang) : null);
	const todayIdx = $derived(P && st ? Math.max(0, Math.min(st.ti, P.days - 1)) : 0);
	const sel = $derived(P ? Math.max(0, Math.min(plansStore.day ?? todayIdx, P.days - 1)) : 0);
	const passages = $derived(s[sel] ?? []);
	const keys = $derived(dayKeys(passages, sel));
	const allDone = $derived(!!m && keys.length > 0 && keys.every((k) => m.done.has(k)));
	const dateOf = (d: number) => addDays(st!.start, d);
	const missed = $derived(st ? st.missed.filter((d) => d !== sel) : []);
	const upcoming = $derived.by(() => {
		if (!P || !st) return [];
		const out: number[] = [];
		for (let d = Math.max(sel, st.ti) + 1; d < P.days && out.length < 3; d++) out.push(d);
		return out;
	});
	let showMissed = $state(false);

	const readHref = (p: Passage) => {
		const u = p.units[0];
		return chapterUrl(settings.value.version, u.book, u.c, u.v ? `${u.v[0]}-${u.v[1]}` : undefined);
	};
	const pick = (d: number) => {
		plansStore.day = d;
		scrollTo({ top: 0, behavior: 'smooth' });
	};
</script>

{#if P && m && st && stt}
	<div class="col">
		<PlanChips pct />

		<header class="head">
			<div class="kicker" lang={other}>{P.title[other]}</div>
			<h1 lang={lang}>{P.title[lang]}</h1>
			<div class="bar-row">
				<div class="bar"><div style:width="{st.pct}%"></div></div>
				<span class="pct">{st.pct}%</span>
			</div>
			<div class="meta" lang={lang}>
				<span>{st.ti < 0 ? (ta ? 'விரைவில் தொடங்கும்' : 'Starting soon') : ta ? `நாள் ${todayIdx + 1} / ${P.days}` : `Day ${todayIdx + 1} of ${P.days}`}</span>
				<span class="status" style:color={tone[stt.tone]}>{stt.text}</span>
				<a class="more" href="/plans/stats">{ta ? 'புள்ளிவிவரம்' : 'Stats'} ›</a>
			</div>
		</header>

		<section class="day" aria-labelledby="day-title">
			<div class="day-head">
				<div class="day-title">
					<h2 id="day-title" lang={lang}>{sel === st.ti ? (ta ? 'இன்று' : 'Today') : weekDate(dateOf(sel), lang)}</h2>
					<span class="sub" lang={lang}>{ta ? `நாள் ${sel + 1} / ${P.days}` : `Day ${sel + 1} of ${P.days}`}{sel === st.ti ? ` · ${shortDate(dateOf(sel), lang)}` : ''}</span>
				</div>
				{#if sel !== todayIdx}
					<button type="button" class="link" lang={lang} onclick={() => (plansStore.day = null)}>{ta ? 'இன்று' : 'Today'} ›</button>
				{/if}
				<button type="button" class="step" aria-label={ta ? 'முந்தைய நாள்' : 'Previous day'} disabled={sel === 0} onclick={() => (plansStore.day = sel - 1)}>‹</button>
				<button type="button" class="step" aria-label={ta ? 'அடுத்த நாள்' : 'Next day'} disabled={sel === P.days - 1} onclick={() => (plansStore.day = sel + 1)}>›</button>
			</div>

			{#each passages as p (p.ti)}
				{@const on = m.done.has(key(sel, p.ti))}
				<div class="passage" class:on>
					<button type="button" class="box" class:on role="checkbox" aria-checked={on}
						aria-label={passageLabel(p.units, lang)}
						onclick={() => plansStore.setDone(P.id, [key(sel, p.ti)], !on)}>{on ? '✓' : ''}</button>
					<div class="p-text">
						<span class="track" lang={lang}>{p.track[lang]}</span>
						<span class="label" lang={lang}>{passageLabel(p.units, lang)}</span>
					</div>
					<a class="read" href={readHref(p)} lang={lang}>{ta ? 'வாசி' : 'Read'} ›</a>
				</div>
			{/each}
			{#if !passages.length}
				<div class="rest" lang={lang}>{ta ? 'ஓய்வு நாள் — பின்தங்கியவற்றை வாசிக்க இதைப் பயன்படுத்துங்கள்.' : 'A spare day — use it to catch up.'}</div>
			{/if}
			{#if passages.length > 1}
				<button type="button" class="all" class:done={allDone} lang={lang} onclick={() => plansStore.setDone(P.id, keys, !allDone)}>
					{allDone ? (ta ? 'வாசித்தது ✓' : 'Day complete ✓') : ta ? 'அனைத்தும் வாசித்தேன்' : 'Mark day read'}
				</button>
			{/if}
		</section>

		{#if missed.length}
			<section class="missed">
				<button type="button" class="missed-head" aria-expanded={showMissed} onclick={() => (showMissed = !showMissed)}>
					<span class="dot"></span>
					<span class="missed-n" lang={lang}>{ta ? `${missed.length} நாள் வாசிக்க வேண்டியவை` : `${missed.length} ${missed.length === 1 ? 'day' : 'days'} to catch up`}</span>
					<span class="toggle" lang={lang}>{showMissed ? (ta ? 'மறை ▴' : 'Hide ▴') : ta ? 'காட்டு ▾' : 'Show ▾'}</span>
				</button>
				{#if showMissed}
					{#each missed as d (d)}
						<div class="missed-row">
							<button type="button" class="box small" role="checkbox" aria-checked="false"
								aria-label={ta ? 'வாசித்ததாகக் குறி' : 'Mark read'}
								onclick={() => plansStore.setDone(P.id, dayKeys(s[d], d), true)}></button>
							<button type="button" class="row-link" onclick={() => pick(d)}>
								<span class="date" lang={lang}>{weekDate(dateOf(d), lang)}</span>
								<span class="labels" lang={lang}>{dayLabel(s[d], lang)}</span>
							</button>
						</div>
					{/each}
				{/if}
			</section>
		{/if}

		{#if upcoming.length}
			<section class="upcoming">
				<span class="kicker" lang={lang}>{ta ? 'அடுத்து' : 'Coming up'}</span>
				{#each upcoming as d (d)}
					<button type="button" class="row-link up" onclick={() => pick(d)}>
						<span class="date" lang={lang}>{weekDate(dateOf(d), lang)}</span>
						<span class="labels" lang={lang}>{dayLabel(s[d], lang)}</span>
					</button>
				{/each}
			</section>
		{/if}
	</div>
{:else}
	<div class="empty">
		<h1 lang={lang}>{ta ? 'இன்னும் திட்டம் இல்லை' : 'No plan yet'}</h1>
		<p lang={lang}>{ta ? 'ஒரு வாசிப்புத் திட்டத்தைத் தேர்ந்தெடுங்கள்; இன்றைய பகுதிகள் இங்கே தோன்றும்.' : "Pick a reading plan and today's passages will appear here."}</p>
		<a class="chip primary" href="/plans/browse" lang={lang}>{ta ? 'திட்டம் தேர்வு' : 'Choose a plan'}</a>
	</div>
{/if}

<style>
	[lang='ta'] { font-family: var(--tamil); }
	.col { max-width: 45rem; margin: 0 auto; display: flex; flex-direction: column; gap: 1.9rem; }
	.head { display: flex; flex-direction: column; gap: 0.75rem; }
	h1 { margin: 0; font-size: 2.1rem; font-weight: 600; line-height: 1.15; color: var(--ink); }
	.bar-row { display: flex; align-items: center; gap: 0.9rem; padding-top: 0.25rem; }
	.bar { flex: 1; height: 6px; border-radius: 999px; background: var(--line-2); overflow: hidden; }
	.bar div { height: 100%; background: var(--accent); border-radius: 999px; }
	.pct { font-size: 0.88rem; font-weight: 800; color: var(--accent); }
	.meta { display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.82rem; color: var(--muted); }
	.status { font-weight: 600; }
	.more { margin-left: auto; font-weight: 700; text-decoration: none; }

	.day { display: flex; flex-direction: column; gap: 0.9rem; padding: 1.6rem; border-radius: var(--r-xl); background: var(--surface-2); border: var(--bw) solid var(--line); }
	.day-head { display: flex; align-items: center; gap: 0.6rem; }
	.day-title { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.2rem; }
	h2 { margin: 0; font-size: 1.6rem; font-weight: 600; color: var(--ink); }
	.sub { font-size: 0.82rem; color: var(--muted); }
	.link { background: none; border: 0; font-size: 0.76rem; font-weight: 700; color: var(--accent); cursor: pointer; padding: 0.5rem 0.6rem; }
	.step { width: 38px; height: 38px; border-radius: 10px; border: var(--bw) solid var(--line-2); background: transparent; color: var(--ink-2); font-size: 1.1rem; cursor: pointer; }
	.step:hover:not(:disabled) { background: var(--surface-3); }
	.step:disabled { opacity: 0.4; cursor: default; }

	.passage { display: flex; align-items: center; gap: 1rem; padding: 1.1rem; border-radius: 14px; background: var(--surface); border: var(--bw) solid var(--line-2); }
	.passage.on { border-color: var(--line); }
	.box { width: 28px; height: 28px; flex: none; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 800; background: transparent; border: 2px solid var(--muted); color: var(--on-accent); padding: 0; }
	.box:hover { border-color: var(--accent); }
	.box.on { background: var(--accent); border-color: var(--accent); }
	.box.small { width: 22px; height: 22px; border-radius: 7px; }
	.p-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.2rem; }
	.track { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
	.label { font-size: 1.45rem; font-weight: 600; line-height: 1.3; color: var(--ink); }
	.passage.on .label { color: var(--muted); }
	.read { flex: none; font-size: 0.88rem; font-weight: 700; color: var(--accent); border: var(--bw) solid var(--line-2); border-radius: 10px; padding: 0.6rem 0.9rem; text-decoration: none; white-space: nowrap; }
	.read:hover { background: var(--surface-3); color: var(--accent); }
	.rest { padding: 1rem 1.1rem; border-radius: 14px; border: var(--bw) dashed var(--line-2); font-size: 0.88rem; line-height: 1.6; color: var(--muted); }
	.all { align-self: flex-start; padding: 0.75rem 1.25rem; border-radius: var(--r); font-size: 0.88rem; font-weight: 700; cursor: pointer; background: var(--accent); color: var(--on-accent); border: var(--bw) solid var(--accent); }
	.all.done { background: transparent; color: var(--accent); }

	.missed { display: flex; flex-direction: column; gap: 0.5rem; }
	.missed-head { display: flex; align-items: center; gap: 0.75rem; padding: 0.9rem 1.1rem; border-radius: 14px; border: var(--bw) solid color-mix(in srgb, var(--bad) 40%, var(--line)); background: transparent; cursor: pointer; text-align: left; }
	.missed-head:hover { background: var(--surface-2); }
	.dot { width: 9px; height: 9px; border-radius: 999px; background: var(--bad); flex: none; }
	.missed-n { font-size: 0.88rem; font-weight: 600; color: var(--ink); }
	.toggle { margin-left: auto; font-size: 0.82rem; font-weight: 700; color: var(--bad); }
	.missed-row { display: flex; align-items: center; gap: 0.9rem; padding: 0.3rem 1.1rem; }
	.row-link { flex: 1; min-width: 0; display: flex; gap: 0.9rem; align-items: baseline; background: none; border: 0; padding: 0.4rem 0; cursor: pointer; text-align: left; }
	.date { width: 7rem; flex: none; font-size: 0.82rem; font-weight: 600; color: var(--muted); }
	.labels { flex: 1; min-width: 0; font-size: 0.88rem; font-weight: 600; color: var(--ink); }
	.row-link:hover .labels { color: var(--accent); }

	.upcoming { display: flex; flex-direction: column; gap: 0.25rem; }
	.upcoming .kicker { padding-bottom: 0.4rem; }
	.up { padding: 0.6rem 0.75rem; border-radius: var(--r); }
	.up:hover { background: var(--surface-2); }
	.up .labels { font-weight: 400; color: var(--ink-2); }

	.empty { max-width: 32rem; margin: 5rem auto 0; display: flex; flex-direction: column; align-items: center; gap: 1rem; text-align: center; }
	.empty h1 { font-size: 1.9rem; }
	.empty p { margin: 0; font-size: 0.95rem; line-height: 1.6; color: var(--muted); }

	@media (max-width: 640px) {
		h1 { font-size: 1.7rem; }
		.day { padding: 1rem; }
		.passage { padding: 0.9rem; gap: 0.75rem; }
		.label { font-size: 1.2rem; }
		.date { width: 5.8rem; }
	}
</style>

<script lang="ts">
	// Stats (design 14A): how far along the plan is, against where it should be,
	// and every day of it as a calendar or a list; a day opens on Today.
	import { goto } from '$app/navigation';
	import { settings } from '$lib/settings/store.svelte';
	import { plansStore } from '$lib/plans/store.svelte';
	import PlanChips from '$lib/plans/PlanChips.svelte';
	import { tone } from '$lib/plans/tone';
	import {
		addDays, dayDone, dayKeys, dayLabel, daysBetween, key, longDate, monthName, schedule, shortDate, stats, status, weekDate
	} from '$lib/plans/schedule';

	const lang = $derived(settings.value.uiLang);
	const ta = $derived(lang === 'ta');

	const P = $derived(plansStore.active);
	const m = $derived(P ? plansStore.progress(P.id) : null);
	const s = $derived(P ? schedule(P) : []);
	const st = $derived(P && m ? stats(P, m) : null);
	const stt = $derived(st ? status(st, lang) : null);
	let view = $state<'cal' | 'list'>('cal');

	type Cell = 'rest-past' | 'rest' | 'full' | 'part' | 'missed' | 'ahead';
	function cellOf(d: number): { cls: Cell; read: number } {
		const day = s[d], read = day.filter((p) => m!.done.has(key(d, p.ti))).length;
		if (!day.length) return { cls: d < st!.ti ? 'rest-past' : 'rest', read };
		if (read === day.length) return { cls: 'full', read };
		if (read > 0) return { cls: 'part', read };
		return { cls: d < st!.ti ? 'missed' : 'ahead', read };
	}

	const months = $derived.by(() => {
		if (!P || !st) return [];
		const out: { label: string; cells: ({ d: number; date: Date; cls: Cell } | null)[]; count: string }[] = [];
		let cur = new Date(st.start.getFullYear(), st.start.getMonth(), 1);
		while (cur <= st.end) {
			const dim = new Date(cur.getFullYear(), cur.getMonth() + 1, 0).getDate();
			const cells: (typeof out)[number]['cells'] = [];
			let n = 0, total = 0;
			for (let i = 1; i <= dim; i++) {
				const date = new Date(cur.getFullYear(), cur.getMonth(), i), d = daysBetween(date, st.start);
				if (d < 0 || d >= P.days) { cells.push(null); continue; }
				const { cls } = cellOf(d);
				if (s[d].length) { total++; if (cls === 'full') n++; }
				cells.push({ d, date, cls });
			}
			out.push({ label: `${monthName(cur.getMonth(), lang)} ${String(cur.getFullYear()).slice(2)}`, cells, count: total ? `${n}/${total}` : '' });
			cur = new Date(cur.getFullYear(), cur.getMonth() + 1, 1);
		}
		return out;
	});

	function open(d: number) {
		plansStore.day = d;
		goto('/plans');
	}
	const listStatus = (d: number) => {
		const { cls } = cellOf(d);
		if (cls === 'rest' || cls === 'rest-past') return { text: ta ? 'ஓய்வு' : 'Rest', color: 'var(--muted)' };
		if (cls === 'full') return { text: ta ? 'வாசித்தது' : 'Read', color: 'var(--accent)' };
		if (cls === 'part') return { text: ta ? 'பகுதி' : 'Partly', color: 'var(--muted)' };
		if (cls === 'missed') return { text: ta ? 'தவறியது' : 'Missed', color: 'var(--bad)' };
		if (d === st!.ti) return { text: ta ? 'இன்று' : 'Today', color: 'var(--ink)' };
		return { text: '—', color: 'var(--muted)' };
	};
</script>

{#if P && m && st && stt}
	<div class="wrap">
		<div class="top">
			<div class="title">
				<span class="kicker" lang={lang}>{ta ? 'புள்ளிவிவரம்' : 'Stats'}</span>
				<h1 lang={lang}>{P.title[lang]}</h1>
			</div>
			<PlanChips />
		</div>

		<div class="tiles">
			<div class="tile"><span class="big accent">{st.pct}%</span><span class="cap" lang={lang}>{ta ? 'முடிந்தது' : 'complete'}</span></div>
			<div class="tile"><span class="big">{st.streak}</span><span class="cap" lang={lang}>{ta ? 'தொடர் நாட்கள்' : 'day streak'}</span></div>
			<div class="tile"><span class="big">{st.chapters}</span><span class="cap" lang={lang}>/ {st.chaptersTotal} {ta ? 'அதிகாரங்கள்' : 'chapters'}</span></div>
			<div class="tile">
				<span class="big date" lang={lang}>{st.finished ? (ta ? 'முடிந்தது' : 'Finished') : st.est ? longDate(st.est, lang) : '—'}</span>
				<span class="cap" lang={lang}>{ta ? 'கணிக்கப்பட்ட முடிவு' : 'est. finish'}</span>
			</div>
		</div>

		<div class="track">
			<div class="bar">
				<div class="fill" style:width="{st.pct}%"></div>
				<div class="now" style:left="{st.expPct}%" title={ta ? 'இன்று இருக்க வேண்டிய இடம்' : 'Where you should be today'}></div>
			</div>
			<div class="meta" lang={lang}>
				<span class="status" style:color={tone[stt.tone]}>{stt.text}</span>
				<span>{stt.sub}</span>
				<span class="range">{longDate(st.start, lang)} → {longDate(st.end, lang)}</span>
			</div>
		</div>

		<section class="panel">
			<div class="panel-head">
				<div class="seg" role="group" aria-label={ta ? 'காட்சி' : 'View'}>
					<button type="button" class:on={view === 'cal'} aria-pressed={view === 'cal'} lang={lang} onclick={() => (view = 'cal')}>{ta ? 'நாட்காட்டி' : 'Calendar'}</button>
					<button type="button" class:on={view === 'list'} aria-pressed={view === 'list'} lang={lang} onclick={() => (view = 'list')}>{ta ? 'பட்டியல்' : 'List'}</button>
				</div>
				<div class="legend" lang={lang}>
					<span><i class="c full"></i>{ta ? 'வாசித்தது' : 'Read'}</span>
					<span><i class="c part"></i>{ta ? 'பகுதி' : 'Partly'}</span>
					<span><i class="c missed"></i>{ta ? 'தவறியது' : 'Missed'}</span>
					<span><i class="c ahead"></i>{ta ? 'வரவிருப்பவை' : 'Ahead'}</span>
				</div>
			</div>

			{#if view === 'cal'}
				<div class="cal">
					{#each months as mo (mo.label)}
						<div class="month">
							<span class="mlabel" lang={lang}>{mo.label}</span>
							<div class="cells">
								{#each mo.cells as c, i (i)}
									{#if c}
										<button type="button" class="c {c.cls}" class:today={c.d === st.ti}
											title="{shortDate(c.date, lang)} · {dayLabel(s[c.d], lang)}"
											aria-label="{weekDate(c.date, lang)} · {dayLabel(s[c.d], lang)}"
											onclick={() => open(c.d)}></button>
									{:else}
										<span class="c none"></span>
									{/if}
								{/each}
							</div>
							<span class="mcount">{mo.count}</span>
						</div>
					{/each}
				</div>
			{:else}
				<div class="list">
					{#each s as day, d (d)}
						{@const done = day.length > 0 && dayDone(day, d, m.done)}
						{@const ls = listStatus(d)}
						<div class="row" class:today={d === st.ti}>
							{#if day.length}
								<button type="button" class="box" class:on={done} role="checkbox" aria-checked={done}
									aria-label={ta ? `நாள் ${d + 1}` : `Day ${d + 1}`}
									onclick={() => plansStore.setDone(P.id, dayKeys(day, d), !done)}>{done ? '✓' : ''}</button>
							{:else}
								<span class="box ghost"></span>
							{/if}
							<span class="n" lang={lang}>{ta ? `நாள் ${d + 1}` : `Day ${d + 1}`}</span>
							<span class="date" lang={lang}>{weekDate(addDays(st.start, d), lang)}</span>
							<button type="button" class="labels" lang={lang} onclick={() => open(d)}>{dayLabel(day, lang)}</button>
							<span class="st" lang={lang} style:color={ls.color}>{ls.text}</span>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	</div>
{:else}
	<div class="empty">
		<h1 lang={lang}>{ta ? 'புள்ளிவிவரம் இல்லை' : 'No stats yet'}</h1>
		<p lang={lang}>{ta ? 'ஒரு திட்டத்தைத் தொடங்கினால் உங்கள் முன்னேற்றம் இங்கே தெரியும்.' : 'Start a plan to see your progress here.'}</p>
		<a class="chip primary" href="/plans/browse" lang={lang}>{ta ? 'திட்டம் தேர்வு' : 'Choose a plan'}</a>
	</div>
{/if}

<style>
	[lang='ta'] { font-family: var(--tamil); }
	.wrap { max-width: 69rem; margin: 0 auto; display: flex; flex-direction: column; gap: 1.75rem; }
	.top { display: flex; align-items: flex-end; gap: 1.25rem; flex-wrap: wrap; }
	.title { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.25rem; }
	h1 { margin: 0; font-size: 1.9rem; font-weight: 600; color: var(--ink); }

	.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.9rem; }
	.tile { padding: 1.25rem 1.4rem; border-radius: var(--r-l); background: var(--surface-2); border: var(--bw) solid var(--line); display: flex; flex-direction: column; gap: 0.4rem; }
	.big { font-family: var(--tamil); font-size: 2.5rem; font-weight: 600; line-height: 1; color: var(--ink); }
	.big.accent { color: var(--accent); }
	.big.date { font-size: 1.6rem; line-height: 1.5; }
	.cap { font-size: 0.75rem; color: var(--muted); }

	.track { display: flex; flex-direction: column; gap: 0.6rem; }
	.bar { position: relative; height: 10px; border-radius: 999px; background: var(--line-2); }
	.fill { position: absolute; inset: 0 auto 0 0; background: var(--accent); border-radius: 999px; }
	.now { position: absolute; top: -4px; bottom: -4px; width: 2px; background: var(--ink); border-radius: 2px; }
	.meta { display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.82rem; color: var(--muted); }
	.status { font-weight: 700; }
	.range { margin-left: auto; }

	.panel { display: flex; flex-direction: column; gap: 1rem; padding: 1.5rem; border-radius: var(--r-l); background: var(--surface-2); border: var(--bw) solid var(--line); }
	.panel-head { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
	.seg { display: flex; border: var(--bw) solid var(--line-2); border-radius: 10px; overflow: hidden; }
	.seg button { padding: 0.5rem 0.9rem; border: 0; background: var(--surface); color: var(--ink-2); font-size: 0.82rem; font-weight: 700; cursor: pointer; }
	.seg button.on { background: var(--accent); color: var(--on-accent); }
	.legend { margin-left: auto; display: flex; gap: 0.9rem; flex-wrap: wrap; font-size: 0.75rem; color: var(--muted); }
	.legend span { display: flex; align-items: center; gap: 0.4rem; }
	.legend .c { width: 11px; height: 11px; border-radius: 3px; }

	.c { display: block; width: 100%; aspect-ratio: 1; max-width: 20px; border-radius: 4px; border: 0; padding: 0; background: transparent; }
	button.c { cursor: pointer; }
	.c.full { background: var(--accent); }
	.c.part { background: color-mix(in srgb, var(--accent) 45%, var(--surface)); }
	.c.missed { background: color-mix(in srgb, var(--bad) 50%, var(--surface)); }
	.c.ahead { background: var(--surface-3); box-shadow: inset 0 0 0 1px var(--line-2); }
	.c.rest { background: var(--surface); }
	.c.rest-past { background: color-mix(in srgb, var(--accent) 18%, var(--surface)); }
	.c.today { box-shadow: 0 0 0 2px var(--ink); }
	.cal { display: flex; flex-direction: column; gap: 6px; }
	.month { display: flex; align-items: center; gap: 0.75rem; }
	.mlabel { width: 4rem; flex: none; font-size: 0.75rem; font-weight: 600; color: var(--muted); }
	.cells { flex: 1; min-width: 0; display: grid; grid-template-columns: repeat(31, minmax(0, 20px)); gap: 5px; }
	.mcount { width: 3.5rem; flex: none; text-align: right; font-size: 0.75rem; font-weight: 700; color: var(--muted); }

	.list { display: flex; flex-direction: column; max-height: 36rem; overflow-y: auto; }
	.row { display: flex; align-items: center; gap: 1rem; padding: 0.7rem 0.4rem; border-bottom: 1px solid var(--line); }
	.row.today { background: var(--surface); }
	.box { width: 22px; height: 22px; flex: none; border-radius: 7px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; color: var(--on-accent); background: transparent; border: 2px solid var(--muted); padding: 0; }
	.box.on { background: var(--accent); border-color: var(--accent); }
	.box.ghost { border-color: transparent; cursor: default; }
	.n { width: 4.4rem; flex: none; font-size: 0.75rem; font-weight: 700; color: var(--muted); }
	.date { width: 7.5rem; flex: none; font-size: 0.82rem; color: var(--muted); }
	.labels { flex: 1; min-width: 0; text-align: left; background: none; border: 0; padding: 0; font-size: 0.88rem; font-weight: 600; color: var(--ink); cursor: pointer; }
	.labels:hover { color: var(--accent); }
	.st { width: 6.5rem; flex: none; text-align: right; font-size: 0.75rem; font-weight: 700; }

	.empty { max-width: 32rem; margin: 5rem auto 0; display: flex; flex-direction: column; align-items: center; gap: 1rem; text-align: center; }
	.empty p { margin: 0; font-size: 0.95rem; color: var(--muted); }

	@media (max-width: 800px) {
		.tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		.range { margin-left: 0; }
	}
	@media (max-width: 640px) {
		.panel { padding: 1rem; }
		.cells { gap: 2px; }
		.c { border-radius: 2px; }
		.mlabel { width: 2.8rem; }
		.mcount { width: 2.4rem; }
		.month { gap: 0.4rem; }
		.big { font-size: 2rem; }
		.n, .st { display: none; }
		.date { width: 5.8rem; }
		.row { gap: 0.6rem; }
	}
</style>

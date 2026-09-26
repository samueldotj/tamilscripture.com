<script lang="ts">
	// Plans (design 14A): the catalogue, joined plans first. A plan starts today
	// or on the first of next month; any number can run side by side.
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { settings } from '$lib/settings/store.svelte';
	import { session } from '$lib/supabase/session.svelte';
	import { plansStore } from '$lib/plans/store.svelte';
	import { lengthLabel, planChapters, shortDate, stats, today, type Plan } from '$lib/plans/schedule';

	const lang = $derived(settings.value.uiLang);
	const ta = $derived(lang === 'ta');
	const other = $derived(ta ? 'en' : 'ta');

	const t = today();
	const nextMonth = new Date(t.getFullYear(), t.getMonth() + 1, 1);
	let confirmLeave = $state<string | null>(null);

	const groups = $derived(
		[
			{ label: ta ? 'என் திட்டங்கள்' : 'My plans', items: plansStore.plans.filter((p) => plansStore.mine[p.id]) },
			{ label: ta ? 'மேலும் திட்டங்கள்' : 'More plans', items: plansStore.plans.filter((p) => !plansStore.mine[p.id]) }
		].filter((g) => g.items.length)
	);

	function perDay(p: Plan) {
		const n = planChapters(p);
		const a = (n / p.days).toFixed(1).replace(/\.0$/, '');
		return ta ? `${n} அதிகாரங்கள் · நாளுக்கு ~${a}` : `${n} chapters · ~${a} a day`;
	}
	function start(p: Plan, d: Date) {
		plansStore.join(p.id, d);
		goto('/plans');
	}
	function open(p: Plan) {
		plansStore.pick(p.id);
		goto('/plans');
	}
	function leave(p: Plan) {
		if (confirmLeave !== p.id) {
			confirmLeave = p.id;
			return;
		}
		plansStore.leave(p.id);
		confirmLeave = null;
	}
</script>

<div class="wrap">
	<header>
		<h1 lang={lang}>{ta ? 'வாசிப்புத் திட்டங்கள்' : 'Reading plans'}</h1>
		<p class="lede" lang={lang}>{ta ? 'எத்தனை திட்டங்களிலும் சேரலாம்' : 'Join as many as you like'}</p>
	</header>

	{#each groups as g (g.label)}
		<section>
			<h2 class="kicker" lang={lang}>{g.label}</h2>
			<div class="grid">
				{#each g.items as p (p.id)}
					{@const joined = !!plansStore.mine[p.id]}
					<article class="card" class:current={joined && p.id === plansStore.active?.id}>
						<div class="tags">
							<span class="tag" lang={lang}>{lengthLabel(p.days, lang)}</span>
							{#if p.community}<span class="tag community" lang={lang}>{ta ? 'சபை' : 'Community'}</span>{/if}
						</div>
						<div class="names">
							<h3 lang={lang}>{p.title[lang]}</h3>
							{#if p.title[other] !== p.title[lang]}<span class="alt" lang={other}>{p.title[other]}</span>{/if}
						</div>
						<p class="blurb" lang={p.community ? undefined : lang}>{p.blurb[lang]}</p>
						<div class="meta" lang={lang}>{perDay(p)}</div>
						{#if joined}
							{@const pct = stats(p, plansStore.progress(p.id)!).pct}
							<div class="bar-row">
								<div class="bar"><div style:width="{pct}%"></div></div>
								<span class="pct">{pct}%</span>
							</div>
							<div class="actions">
								<button type="button" class="btn primary" lang={lang} onclick={() => open(p)}>{ta ? 'தொடர்' : 'Continue'}</button>
								<button type="button" class="leave" class:confirm={confirmLeave === p.id} lang={lang} onclick={() => leave(p)}>
									{confirmLeave === p.id ? (ta ? 'உறுதியா? நிறுத்து' : 'Confirm leave') : ta ? 'நிறுத்து' : 'Leave'}
								</button>
							</div>
						{:else}
							<div class="actions">
								<button type="button" class="btn primary" lang={lang} onclick={() => start(p, t)}>{ta ? 'இன்று தொடங்கு' : 'Start today'}</button>
								<button type="button" class="btn" lang={lang} onclick={() => start(p, nextMonth)}>{ta ? `${shortDate(nextMonth, lang)} அன்று` : `Start ${shortDate(nextMonth, lang)}`}</button>
							</div>
						{/if}
					</article>
				{/each}
			</div>
		</section>
	{/each}

	{#if session.ready && !session.signedIn}
		<p class="note" lang={lang}>
			{ta ? 'உங்கள் முன்னேற்றம் இந்த உலாவியில் மட்டும் சேமிக்கப்படுகிறது.' : 'Your progress is kept in this browser only.'}
			<a href="/signin?next={encodeURIComponent(page.url.pathname)}">{ta ? 'உள்நுழைந்தால்' : 'Sign in'}</a>
			{ta ? 'எல்லா சாதனங்களிலும் தொடரலாம்.' : 'to carry it to all your devices.'}
		</p>
	{/if}
</div>

<style>
	[lang='ta'] { font-family: var(--tamil); }
	.wrap { max-width: 69rem; margin: 0 auto; display: flex; flex-direction: column; gap: 2.1rem; }
	header { display: flex; flex-direction: column; gap: 0.25rem; }
	h1 { margin: 0; font-size: 2.1rem; font-weight: 600; color: var(--ink); }
	.lede { margin: 0; font-size: 0.88rem; color: var(--muted); }
	section { display: flex; flex-direction: column; gap: 0.9rem; }
	h2 { margin: 0; }
	.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
	.card { display: flex; flex-direction: column; gap: 0.9rem; padding: 1.4rem; background: var(--surface-2); border-radius: var(--r-l); }
	.card.current { border-color: var(--line-2); }
	.tags { display: flex; gap: 0.5rem; flex-wrap: wrap; }
	.tag { font-size: 0.75rem; font-weight: 700; color: var(--ink-2); border: var(--bw) solid var(--line-2); border-radius: 999px; padding: 3px 10px; }
	.tag.community { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 45%, var(--line-2)); }
	.names { display: flex; flex-direction: column; gap: 0.25rem; }
	h3 { margin: 0; font-size: 1.3rem; font-weight: 600; line-height: 1.25; color: var(--ink); }
	.alt { font-size: 0.75rem; color: var(--muted); }
	.blurb { flex: 1; margin: 0; font-size: 0.82rem; line-height: 1.6; color: var(--muted); text-wrap: pretty; }
	.meta { font-size: 0.75rem; font-weight: 600; color: var(--muted); }
	.bar-row { display: flex; align-items: center; gap: 0.6rem; }
	.bar { flex: 1; height: 5px; border-radius: 999px; background: var(--line-2); overflow: hidden; }
	.bar div { height: 100%; background: var(--accent); }
	.pct { font-size: 0.82rem; font-weight: 800; color: var(--accent); }
	.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
	.btn { padding: 0.6rem 1rem; border-radius: 10px; border: var(--bw) solid var(--line-2); background: transparent; color: var(--ink); font-size: 0.82rem; font-weight: 700; cursor: pointer; }
	.btn:hover { background: var(--surface-3); }
	.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.btn.primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
	.leave { margin-left: auto; background: none; border: 0; font-size: 0.75rem; font-weight: 700; color: var(--muted); cursor: pointer; padding: 0.5rem 0.25rem; }
	.leave.confirm { color: var(--bad); }
	.note { margin: 0; font-size: 0.85rem; color: var(--muted); }
	@media (max-width: 960px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
	@media (max-width: 640px) {
		h1 { font-size: 1.7rem; }
		.grid { grid-template-columns: minmax(0, 1fr); }
	}
</style>

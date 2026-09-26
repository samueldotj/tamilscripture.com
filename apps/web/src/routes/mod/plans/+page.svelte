<script lang="ts">
	// Create plans (design 14A, moderator): community plans are drafted and
	// published here; published ones appear for everyone on /plans/browse. The
	// database lets only moderators write (reading_plans RLS); this page only
	// decides what to render.
	import { getContext } from 'svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { manifest } from '$lib/content/manifest';
	import { allPlans, deletePlan, savePlan, type PlanDraft } from '$lib/plans/repo';
	import {
		DURATIONS, LIMITS, bookRange, dayLabel, fromRow, lengthLabel, planChapters, schedule, type PlanRow
	} from '$lib/plans/schedule';

	const roleBox = getContext<{ value: string | null }>('mod-role');
	const lang = $derived(settings.value.uiLang);
	const ta = $derived(lang === 'ta');

	const blank = (): PlanDraft => ({ title_ta: '', title_en: '', blurb: '', days: 90, tracks: [{ name: 'பகுதி 1', from: 'MAT', to: 'JHN' }] });
	let list = $state<PlanRow[]>([]);
	let loaded = $state(false);
	let editing = $state<string | null>(null);
	let form = $state<PlanDraft>(blank());
	let flash = $state('');
	let err = $state('');
	let busy = $state(false);
	let confirmDel = $state(false);

	$effect(() => {
		if (roleBox.value !== 'moderator') return;
		allPlans().then((r) => { list = r; loaded = true; }).catch((e) => { err = e.message; loaded = true; });
	});

	const cur = $derived(list.find((p) => p.id === editing) ?? null);
	const preview = $derived(fromRow({ id: 'preview', ...form }));
	const sched = $derived(preview.tracks.length ? schedule(preview) : []);
	const chapters = $derived(planChapters(preview));
	const errors = $derived.by(() => {
		const e: string[] = [];
		if (!form.title_ta.trim()) e.push(ta ? 'தமிழ்ப் பெயர் சேர்க்கவும்.' : 'Add a Tamil name.');
		if (!preview.tracks.length) e.push(ta ? 'குறைந்தது ஒரு சரியான பகுதி வேண்டும்.' : 'Add at least one valid track (start book before end book).');
		if (form.tracks.some((t) => !bookRange(t.from, t.to).length)) e.push(ta ? 'ஒரு பகுதி தொடங்கும் முன்பே முடிகிறது.' : 'A track ends before it starts.');
		return e;
	});
	const trackInfo = (t: PlanDraft['tracks'][number]) => {
		const books = bookRange(t.from, t.to);
		return books.length ? `${books.reduce((a, b) => a + b.chapters, 0)} ${ta ? 'அதி.' : 'ch.'}` : ta ? 'தவறு' : 'invalid';
	};

	function touch() { flash = ''; err = ''; confirmDel = false; }
	function edit(p: PlanRow) {
		editing = p.id;
		form = { title_ta: p.title_ta, title_en: p.title_en, blurb: p.blurb, days: p.days, tracks: p.tracks.map((t) => ({ ...t })) };
		touch();
	}
	function newPlan() { editing = null; form = blank(); touch(); }
	function addTrack() {
		if (form.tracks.length >= LIMITS.tracks) return;
		form.tracks.push({ name: ta ? `பகுதி ${form.tracks.length + 1}` : `Track ${form.tracks.length + 1}`, from: 'PSA', to: 'PSA' });
		touch();
	}

	async function commit(status: PlanRow['status']) {
		if (busy || (status === 'published' && errors.length) || !form.tracks.length) return;
		busy = true; touch();
		try {
			const row = await savePlan(editing, $state.snapshot(form), status);
			list = editing ? list.map((p) => (p.id === row.id ? row : p)) : [...list, row];
			editing = row.id;
			flash = status === 'published' ? (ta ? 'வெளியிடப்பட்டது' : 'Published') : ta ? 'வரைவு சேமிக்கப்பட்டது' : 'Draft saved';
		} catch (e) {
			err = (e as Error).message;
		} finally {
			busy = false;
		}
	}
	async function remove() {
		if (!editing) return;
		if (!confirmDel) { confirmDel = true; return; }
		busy = true;
		try {
			await deletePlan(editing);
			list = list.filter((p) => p.id !== editing);
			newPlan();
		} catch (e) {
			err = (e as Error).message;
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>{ta ? 'திட்டம் உருவாக்கு' : 'Create plans'}</title></svelte:head>

{#if roleBox.value !== 'moderator'}
	<p class="muted" lang={lang}>{ta ? 'வாசிப்புத் திட்டங்களை மதிப்பீட்டாளர்கள் மட்டுமே உருவாக்க முடியும்.' : 'Only moderators can create reading plans.'}</p>
{:else}
	<div class="editor">
		<aside class="side">
			<button type="button" class="new" lang={lang} onclick={newPlan}>+ {ta ? 'புதிய திட்டம்' : 'New plan'}</button>
			<span class="kicker" lang={lang}>{ta ? 'சபை திட்டங்கள்' : 'Community plans'}</span>
			{#if !loaded}<p class="muted">…</p>{/if}
			{#each list as p (p.id)}
				<button type="button" class="item" class:on={p.id === editing} onclick={() => edit(p)}>
					<span class="item-name" lang="ta">{p.title_ta || p.title_en || (ta ? 'பெயரிடப்படாதது' : 'Untitled')}</span>
					<span class="item-meta" lang={lang}>
						<span>{lengthLabel(p.days, lang)}</span>
						<span class="item-status" class:pub={p.status === 'published'}>{p.status === 'published' ? (ta ? 'வெளியிடப்பட்டது' : 'Published') : ta ? 'வரைவு' : 'Draft'}</span>
					</span>
				</button>
			{/each}
		</aside>

		<div class="form">
			<header>
				<h1 lang={lang}>{editing ? (ta ? 'திட்டத்தைத் திருத்து' : 'Edit plan') : ta ? 'புதிய திட்டம்' : 'New plan'}</h1>
				<p class="muted" lang={lang}>{ta ? 'வெளியிட்ட திட்டங்கள் அனைவருக்கும் “திட்டங்கள்” பக்கத்தில் தோன்றும்.' : 'Published plans appear for everyone on the Plans page.'}</p>
			</header>
			<div class="two">
				<label><span lang="ta">பெயர் (தமிழ்)</span>
					<input class="field" lang="ta" maxlength={LIMITS.title} bind:value={form.title_ta} oninput={touch} placeholder="எ.கா. நற்செய்திகள் · 40 நாள்" /></label>
				<label><span>English name</span>
					<input class="field en" maxlength={LIMITS.title} bind:value={form.title_en} oninput={touch} placeholder="e.g. Gospels · 40 days" /></label>
			</div>
			<label><span lang={lang}>{ta ? 'விளக்கம்' : 'Description'}</span>
				<textarea class="field" rows="3" maxlength={LIMITS.blurb} bind:value={form.blurb} oninput={touch}></textarea></label>
			<div class="group">
				<span class="lbl" lang={lang}>{ta ? 'காலம்' : 'Duration'}</span>
				<div class="durs">
					{#each DURATIONS as d (d)}
						<button type="button" class="dur" class:on={form.days === d} aria-pressed={form.days === d} lang={lang}
							onclick={() => { form.days = d; touch(); }}>{lengthLabel(d, lang)}{d >= 90 ? ` · ${d}` : ''}</button>
					{/each}
				</div>
			</div>
			<div class="group">
				<span class="lbl" lang={lang}>{ta ? 'தினசரி பகுதிகள் — ஒவ்வொரு பகுதியும் இணையாக, நாட்களில் சமமாகப் பிரித்து வாசிக்கப்படும்' : 'Daily tracks — each track is read in parallel, split evenly across the days'}</span>
				{#each form.tracks as t, i (i)}
					<div class="trackrow">
						<input class="field tname" maxlength={LIMITS.name} bind:value={t.name} oninput={touch} placeholder={ta ? 'பகுதியின் பெயர்' : 'Track name'} aria-label={ta ? 'பகுதியின் பெயர்' : 'Track name'} />
						<select class="field" bind:value={t.from} onchange={touch} aria-label={ta ? 'தொடக்கப் புத்தகம்' : 'First book'}>
							{#each manifest.books as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
						</select>
						<span class="arrow">→</span>
						<select class="field" bind:value={t.to} onchange={touch} aria-label={ta ? 'கடைசிப் புத்தகம்' : 'Last book'}>
							{#each manifest.books as b (b.code)}<option value={b.code}>{ta ? b.name_ta : b.name_en}</option>{/each}
						</select>
						<span class="info" class:bad={!bookRange(t.from, t.to).length} lang={lang}>{trackInfo(t)}</span>
						<button type="button" class="x" aria-label={ta ? 'நீக்கு' : 'Remove'} onclick={() => { form.tracks.splice(i, 1); touch(); }}>×</button>
					</div>
				{/each}
				{#if form.tracks.length < LIMITS.tracks}
					<button type="button" class="add" lang={lang} onclick={addTrack}>+ {ta ? 'பகுதி சேர்' : 'Add track'}</button>
				{/if}
			</div>
		</div>

		<aside class="preview">
			<div class="pv-head">
				<span class="kicker" lang={lang}>{ta ? 'முன்னோட்டம்' : 'Preview'}</span>
				<span class="pv-title" lang="ta">{form.title_ta || 'பெயரிடப்படாத திட்டம்'}</span>
				<span class="muted" lang={lang}>{ta ? `${form.days} நாள் · ${chapters} அதிகாரங்கள் · நாளுக்கு ~${(chapters / form.days).toFixed(1)}` : `${form.days} days · ${chapters} chapters · ~${(chapters / form.days).toFixed(1)} a day`}</span>
			</div>
			<div class="pv-days">
				{#each sched.slice(0, 7) as day, d (d)}
					<div class="pv-day">
						<span class="pv-n" lang={lang}>{ta ? `நாள் ${d + 1}` : `Day ${d + 1}`}</span>
						<span class="pv-l" lang={lang}>{dayLabel(day, lang)}</span>
					</div>
				{/each}
				{#if sched.length > 7}<span class="muted more" lang={lang}>+ {sched.length - 7} {ta ? 'நாட்கள்' : 'days'}</span>{/if}
			</div>
			{#if errors.length}<p class="errs" lang={lang}>{errors.join(' ')}</p>{/if}
			{#if err}<p class="errs" role="alert">{err}</p>{/if}
			<div class="acts">
				<button type="button" class="btn primary" lang={lang} disabled={busy || errors.length > 0} onclick={() => commit('published')}>
					{cur?.status === 'published' ? (ta ? 'புதுப்பி' : 'Update plan') : ta ? 'வெளியிடு' : 'Publish'}
				</button>
				<button type="button" class="btn" lang={lang} disabled={busy || !form.tracks.length} onclick={() => commit('draft')}>
					{cur?.status === 'published' ? (ta ? 'வரைவாக மாற்று' : 'Unpublish to draft') : ta ? 'வரைவாகச் சேமி' : 'Save draft'}
				</button>
				{#if cur}
					<button type="button" class="del" class:confirm={confirmDel} lang={lang} disabled={busy} onclick={remove}>
						{confirmDel ? (ta ? 'உறுதியா? நீக்கு' : 'Confirm delete') : ta ? 'நீக்கு' : 'Delete plan'}
					</button>
				{/if}
				{#if flash}<span class="flash" role="status" lang={lang}>{flash}</span>{/if}
			</div>
		</aside>
	</div>
{/if}

<style>
	[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); font-size: 0.82rem; margin: 0; }
	.editor { display: grid; grid-template-columns: 15rem minmax(0, 1fr) 20rem; border: var(--bw) solid var(--line); border-radius: var(--r-xl); overflow: hidden; min-height: 36rem; }
	.side, .preview { background: var(--surface-2); padding: 1.4rem 0.9rem; display: flex; flex-direction: column; gap: 0.5rem; }
	.side { border-right: var(--bw) solid var(--line); }
	.preview { border-left: var(--bw) solid var(--line); padding: 1.6rem 1.4rem; gap: 1.2rem; }
	.new { padding: 0.75rem; border-radius: var(--r); border: var(--bw) dashed var(--line-2); background: transparent; color: var(--ink); font-size: 0.88rem; font-weight: 700; cursor: pointer; margin-bottom: 0.75rem; }
	.new:hover { border-color: var(--accent); }
	.side .kicker { padding: 0 0.6rem 0.25rem; }
	.item { display: flex; flex-direction: column; gap: 0.35rem; padding: 0.75rem 0.9rem; border-radius: var(--r); cursor: pointer; background: transparent; border: var(--bw) solid transparent; text-align: left; }
	.item:hover { background: var(--surface-3); }
	.item.on { background: var(--surface-3); border-color: var(--accent); }
	.item-name { font-size: 0.88rem; font-weight: 600; color: var(--ink); }
	.item-meta { display: flex; gap: 0.5rem; font-size: 0.75rem; color: var(--muted); }
	.item-status { margin-left: auto; font-weight: 700; }
	.item-status.pub { color: var(--good); }

	.form { padding: 2rem 2.2rem 2.4rem; display: flex; flex-direction: column; gap: 1.5rem; min-width: 0; }
	header { display: flex; flex-direction: column; gap: 0.25rem; }
	h1 { margin: 0; font-size: 1.75rem; font-weight: 600; }
	.two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.9rem; }
	label, .group { display: flex; flex-direction: column; gap: 0.45rem; }
	label > span, .lbl { font-size: 0.75rem; font-weight: 700; color: var(--muted); }
	.field { border-radius: 10px; padding: 0.7rem 0.85rem; }
	.field.en { font-family: var(--sans); }
	textarea.field { resize: vertical; line-height: 1.55; }
	.durs { display: flex; gap: 0.5rem; flex-wrap: wrap; }
	.dur { padding: 0.55rem 1rem; border-radius: 10px; font-size: 0.82rem; font-weight: 700; cursor: pointer; background: var(--surface); color: var(--ink-2); border: var(--bw) solid var(--line-2); }
	.dur.on { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
	.trackrow { display: flex; align-items: center; gap: 0.6rem; padding: 0.75rem; border-radius: var(--r); border: var(--bw) solid var(--line); background: var(--surface-2); flex-wrap: wrap; }
	.trackrow .tname { width: 10rem; flex: none; }
	.trackrow select { flex: 1; min-width: 8rem; width: auto; padding: 0.6rem; }
	.arrow { color: var(--muted); }
	.info { width: 4rem; flex: none; text-align: right; font-size: 0.75rem; font-weight: 700; color: var(--muted); }
	.info.bad { color: var(--bad); }
	.x { width: 32px; height: 32px; flex: none; border-radius: 8px; border: 0; background: transparent; color: var(--muted); cursor: pointer; font-size: 1.1rem; }
	.x:hover { background: var(--surface-3); color: var(--bad); }
	.add { align-self: flex-start; background: none; border: 0; font-size: 0.82rem; font-weight: 700; color: var(--accent); cursor: pointer; padding: 0.4rem 0; }

	.pv-head { display: flex; flex-direction: column; gap: 0.25rem; }
	.pv-title { font-size: 1.35rem; font-weight: 600; color: var(--ink); }
	.pv-days { display: flex; flex-direction: column; gap: 0.4rem; }
	.pv-day { display: flex; gap: 0.75rem; padding: 0.6rem 0.75rem; border-radius: 10px; border: var(--bw) solid var(--line); }
	.pv-n { width: 3rem; flex: none; font-size: 0.75rem; font-weight: 700; color: var(--accent); }
	.pv-l { flex: 1; min-width: 0; font-size: 0.82rem; line-height: 1.5; color: var(--ink); }
	.more { padding: 0.25rem 0.75rem; }
	.errs { margin: 0; font-size: 0.82rem; line-height: 1.5; color: var(--bad); }
	.acts { margin-top: auto; display: flex; flex-direction: column; gap: 0.6rem; }
	.btn { padding: 0.8rem; border-radius: var(--r); border: var(--bw) solid var(--line-2); background: transparent; color: var(--ink); font-size: 0.88rem; font-weight: 700; cursor: pointer; }
	.btn:hover:not(:disabled) { background: var(--surface-3); }
	.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	.btn.primary:hover:not(:disabled) { background: var(--accent-hover); }
	.btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.del { background: none; border: 0; padding: 0.5rem; font-size: 0.82rem; font-weight: 700; color: var(--muted); cursor: pointer; }
	.del.confirm { color: var(--bad); }
	.flash { text-align: center; font-size: 0.82rem; font-weight: 600; color: var(--good); }

	@media (max-width: 1100px) {
		.editor { grid-template-columns: 14rem minmax(0, 1fr); }
		.preview { grid-column: 1 / -1; border-left: 0; border-top: var(--bw) solid var(--line); }
	}
	@media (max-width: 720px) {
		.editor { grid-template-columns: minmax(0, 1fr); }
		.side { border-right: 0; border-bottom: var(--bw) solid var(--line); }
		.form { padding: 1.25rem; }
		.two { grid-template-columns: minmax(0, 1fr); }
	}
</style>

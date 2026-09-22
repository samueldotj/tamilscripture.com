<script lang="ts">
	// Presentation editor (design 11A): slides in the left rail, the current
	// slide's preview and notes in the middle, its verses and the verse picker
	// on the right. Every change saves itself after a moment and is broadcast
	// to a presenter tab opened from here. Loaded on demand by the edit route
	// so its code stays out of the route-node budget.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { beforeNavigate, goto, replaceState } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';
	import { findVersion, manifest } from '$lib/content/manifest';
	import { myPresentation, presentChannel, presentUrl, savePresentation, type PresentMessage } from '$lib/present/repo';
	import { LIMITS, newId, newSlide, verseLabel, verseVersion, type Presentation, type Slide, type SlideVerse } from '$lib/present/types';
	import SlideRail from '$lib/present/SlideRail.svelte';
	import SlideView from '$lib/present/SlideView.svelte';
	import NotesEditor from '$lib/present/NotesEditor.svelte';
	import VersePicker from '$lib/present/VersePicker.svelte';

	let { slug }: { slug: string } = $props();
	const lang = $derived(settings.value.uiLang);
	const ta = $derived(lang === 'ta');

	let doc = $state<Presentation | null>(null);
	let missing = $state(false);
	let current = $state(0);
	let status = $state<'idle' | 'dirty' | 'saving' | 'saved' | 'error'>('idle');
	let savedAt = $state<Date | null>(null);
	let shareOpen = $state(false);
	let toast = $state('');
	let channel: BroadcastChannel | null = null;
	let timer: ReturnType<typeof setTimeout> | undefined;
	let saving = false;
	let pending = false;

	const slide = $derived(doc && doc.slides[current] ? doc.slides[current] : null);
	const shareUrl = $derived(`https://www.tamilscripture.com${presentUrl(slug)}`);
	const presentHref = $derived(presentUrl(slug, current + 1));

	$effect(() => {
		if (!session.ready) return;
		if (!session.signedIn) {
			goto(`/signin?next=${encodeURIComponent(page.url.pathname)}`, { replaceState: true });
			return;
		}
		if (doc || missing) return;
		myPresentation(slug)
			.then((p) => {
				if (!p) { missing = true; return; }
				if (!p.slides.length) p.slides.push(newSlide());
				doc = p;
				savedAt = new Date(p.updated_at);
				const h = Number(location.hash.slice(1));
				if (h >= 1 && h <= p.slides.length) current = h - 1;
			})
			.catch(() => (missing = true));
	});

	onMount(() => {
		channel = presentChannel(slug);
		if (channel) channel.onmessage = (e: MessageEvent<PresentMessage>) => {
			// Follow the presenter tab as it moves.
			if (e.data.type === 'slide' && doc && e.data.index < doc.slides.length) current = e.data.index;
		};
		const warn = (e: BeforeUnloadEvent) => { if (status === 'dirty' || status === 'saving') { save(); e.preventDefault(); } };
		addEventListener('beforeunload', warn);
		return () => { removeEventListener('beforeunload', warn); channel?.close(); };
	});
	beforeNavigate(() => { if (status === 'dirty') { clearTimeout(timer); save(); } });

	// ---- saving ------------------------------------------------------------------
	function touch() {
		if (!doc) return;
		status = 'dirty';
		clearTimeout(timer);
		timer = setTimeout(save, 800);
		channel?.postMessage({ type: 'doc', presentation: $state.snapshot(doc) } satisfies PresentMessage);
	}
	async function save() {
		if (!doc) return;
		if (saving) { pending = true; return; }
		saving = true;
		status = 'saving';
		const { id, title, subtitle, version, visibility, slides } = $state.snapshot(doc);
		try {
			const saved = await savePresentation(id, { title, subtitle, version, visibility, slides });
			savedAt = new Date(saved.updated_at);
			status = pending ? 'dirty' : 'saved';
		} catch {
			status = 'error';
		} finally {
			saving = false;
			if (pending) { pending = false; save(); }
		}
	}
	const savedText = $derived.by(() => {
		if (status === 'saving') return ta ? 'சேமிக்கிறது…' : 'Saving…';
		if (status === 'error') return ta ? 'சேமிக்க முடியவில்லை' : 'Could not save';
		if (status === 'dirty') return ta ? 'மாற்றங்கள்…' : 'Unsaved changes';
		if (!savedAt) return '';
		const min = Math.round((Date.now() - savedAt.getTime()) / 60000);
		if (min < 1) return ta ? 'இப்போது சேமிக்கப்பட்டது' : 'Saved just now';
		if (min < 60) return ta ? `${min} நிமிடம் முன் சேமிக்கப்பட்டது` : `Saved ${min} min ago`;
		return (ta ? 'சேமிக்கப்பட்டது ' : 'Saved ') + savedAt.toLocaleTimeString(ta ? 'ta-IN' : 'en-IN', { hour: 'numeric', minute: '2-digit' });
	});

	// ---- slides --------------------------------------------------------------------
	function select(i: number) {
		current = i;
		replaceState(i ? `#${i + 1}` : location.pathname, page.state);
	}
	function addSlide() {
		if (!doc || doc.slides.length >= LIMITS.slides) return;
		doc.slides.splice(current + 1, 0, newSlide());
		select(current + 1);
		touch();
	}
	function duplicate() {
		if (!doc || !slide || doc.slides.length >= LIMITS.slides) return;
		doc.slides.splice(current + 1, 0, { ...$state.snapshot(slide), id: newId(8) });
		select(current + 1);
		touch();
	}
	function remove() {
		if (!doc || !slide) return;
		const empty = !slide.verses.length && !slide.notes.trim() && !slide.title?.trim();
		if (!empty && !confirm(ta ? `ஸ்லைடு ${current + 1} நீக்கவா?` : `Delete slide ${current + 1}?`)) return;
		doc.slides.splice(current, 1);
		if (!doc.slides.length) doc.slides.push(newSlide());
		select(Math.min(current, doc.slides.length - 1));
		touch();
	}
	function move(from: number, to: number) {
		if (!doc || from === to) return;
		const [s] = doc.slides.splice(from, 1);
		doc.slides.splice(to, 0, s);
		select(to);
		touch();
	}
	function addVerse(v: SlideVerse) {
		if (!slide || slide.verses.length >= LIMITS.versesPerSlide) return;
		slide.verses.push(v);
		touch();
	}
	function removeVerse(i: number) {
		if (!slide) return;
		slide.verses.splice(i, 1);
		touch();
	}
	function setVerseVersion(i: number, code: string | undefined) {
		if (!slide) return;
		if (code) slide.verses[i].version = code;
		else delete slide.verses[i].version;
		touch();
	}
	const insertLabel = $derived(slide?.verses.length ? verseLabel(slide.verses[0], findVersion(verseVersion(slide.verses[0], doc?.version ?? 'IRVTAM'))?.lang ?? lang) : null);

	// ---- share -----------------------------------------------------------------------
	function flash(msg: string) { toast = msg; setTimeout(() => (toast = ''), 1800); }
	async function copyLink() {
		try { await navigator.clipboard.writeText(shareUrl); flash(ta ? 'இணைப்பு நகலெடுக்கப்பட்டது' : 'Link copied'); }
		catch { flash(shareUrl); }
	}
	async function share() {
		if (navigator.share && doc) { try { await navigator.share({ title: doc.title, url: shareUrl }); } catch { /* cancelled */ } }
		else copyLink();
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') shareOpen = false;
	}
</script>

<svelte:head>
	<title>{doc?.title || (ta ? 'விளக்கக்காட்சி' : 'Presentation')} · {ta ? 'திருத்து' : 'Edit'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<svelte:window onkeydown={onKey} />

{#if missing}
	<section class="state">
		<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'விளக்கக்காட்சி கிடைக்கவில்லை' : 'Presentation not found'}</h1>
		<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'இது உங்களுடையது அல்ல, அல்லது நீக்கப்பட்டது.' : 'It is not yours, or it was deleted.'}</p>
		<p><a href="/me/presentations" lang={ta ? 'ta' : 'en'}>‹ {ta ? 'விளக்கக்காட்சிகள்' : 'Presentations'}</a></p>
	</section>
{:else if !doc || !slide}
	<p class="state muted" aria-busy="true">…</p>
{:else}
	<div class="editor">
		<!-- left rail · slides -->
		<div class="rail-col">
			<div class="rail-head">
				<div class="crumb"><a href="/me/presentations" lang="ta">‹ விளக்கக்காட்சிகள்</a><span>·</span><span class="saved" role="status" class:err={status === 'error'}>{savedText}</span></div>
				<input class="title" lang={/[஀-௿]/.test(doc.title) || !doc.title ? 'ta' : 'en'} bind:value={doc.title} oninput={touch} maxlength={LIMITS.title} placeholder={ta ? 'தலைப்பு' : 'Title'} aria-label={ta ? 'விளக்கக்காட்சியின் தலைப்பு' : 'Presentation title'} />
				<div class="subrow">
					<input class="subtitle" bind:value={doc.subtitle} oninput={touch} maxlength={LIMITS.title} placeholder={ta ? 'துணைத் தலைப்பு' : 'Subtitle'} aria-label={ta ? 'துணைத் தலைப்பு' : 'Subtitle'} />
					<span class="n">· {doc.slides.length} {ta ? 'ஸ்லைடுகள்' : 'slides'}</span>
				</div>
			</div>
			<div class="rail-body">
				<SlideRail slides={doc.slides} {current} {lang} onselect={select} onadd={addSlide} onmove={move} />
			</div>
		</div>

		<!-- centre · canvas + notes -->
		<div class="centre">
			<div class="toolbar">
				<span class="kicker">{ta ? 'ஸ்லைடு' : 'Slide'} {current + 1} / {doc.slides.length}</span>
				<span class="grow"></span>
				<label class="ver-label"><span class="sr">{ta ? 'இயல்பு மொழிபெயர்ப்பு' : 'Default version'}</span>
					<select class="chip ver" bind:value={doc.version} onchange={touch}>
						{#each manifest.versions as v (v.code)}<option value={v.code}>{v.short} · {v.lang === 'ta' ? 'தமிழ்' : 'English'}</option>{/each}
					</select>
				</label>
				<button type="button" class="chip" onclick={duplicate} disabled={doc.slides.length >= LIMITS.slides}><span lang="ta">நகல்</span> · Duplicate</button>
				<button type="button" class="chip" onclick={remove} aria-label={ta ? 'ஸ்லைடை நீக்கு' : 'Delete slide'}>{ta ? 'நீக்கு' : 'Delete'}</button>
				<div class="share-wrap">
					<button type="button" class="chip" aria-expanded={shareOpen} onclick={() => (shareOpen = !shareOpen)} lang="ta">பகிர்</button>
					{#if shareOpen}
						<div class="share card" role="dialog" aria-label={ta ? 'பகிர்' : 'Share'}>
							<p class="kicker">{ta ? 'நிரந்தர இணைப்பு' : 'Permanent link'}</p>
							<div class="link"><input readonly value={shareUrl} aria-label="Link" onfocus={(e) => e.currentTarget.select()} /><button type="button" class="chip primary" onclick={copyLink}>{ta ? 'நகல்' : 'Copy'}</button></div>
							<div class="vis" role="radiogroup" aria-label={ta ? 'யார் பார்க்கலாம்' : 'Who can open it'}>
								<label><input type="radio" name="vis" value="link" bind:group={doc.visibility} onchange={touch} /> <span lang={ta ? 'ta' : 'en'}>{ta ? 'இணைப்பு உள்ள யாரும்' : 'Anyone with the link'}</span></label>
								<label><input type="radio" name="vis" value="private" bind:group={doc.visibility} onchange={touch} /> <span lang={ta ? 'ta' : 'en'}>{ta ? 'நான் மட்டும்' : 'Only me'}</span></label>
							</div>
							<p class="muted small" lang={ta ? 'ta' : 'en'}>{ta ? 'பார்ப்பவர்கள் வேறு மொழிபெயர்ப்பையும் தேர்வு செய்யலாம்; வசனங்கள் தளத்திலிருந்து அப்போது வாசிக்கப்படும்.' : 'Viewers can pick another translation; the verses are read from the site when shown.'}</p>
							{#if 'share' in navigator}<button type="button" class="chip" onclick={share}>{ta ? 'பகிர்…' : 'Share…'}</button>{/if}
						</div>
					{/if}
				</div>
				<a class="chip primary present" href={presentHref} target="_blank" rel="noopener"><span class="play" aria-hidden="true">▶</span><span lang="ta">வழங்கு</span> · Present <kbd>⧉ {ta ? 'புதிய தாவல்' : 'new tab'}</kbd></a>
			</div>
			<div class="canvas-wrap">
				<div class="canvas">
					<SlideView {slide} version={doc.version} {lang} />
				</div>
			</div>
			<label class="slide-title">
				<span class="kicker"><span lang="ta">தலைப்பு</span> · Header</span>
				<input class="field" value={slide.title ?? ''} oninput={(e) => { slide.title = e.currentTarget.value; touch(); }} maxlength={LIMITS.title} placeholder={ta ? 'ஒரு வரி, ஸ்லைடின் மேலே · வசனம் இல்லாத தலைப்புப் பக்கத்தில் பெரிதாக' : 'One line across the top · large on a title page without verses'} />
			</label>
			<div class="notes-wrap">
				<NotesEditor bind:value={slide.notes} version={doc.version} {lang} {insertLabel} onchange={touch} />
			</div>
		</div>

		<!-- right · verses on this slide + picker -->
		<div class="picker">
			<VersePicker {slide} version={doc.version} {lang} onadd={addVerse} onremove={removeVerse} onversion={setVerseVersion} />
		</div>
	</div>
	{#if toast}<div class="toast" role="status">{toast}</div>{/if}
{/if}

<style>
	.state { max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }
	.state h1[lang='ta'], .state a[lang='ta'], .state p[lang='ta'] { font-family: var(--tamil); }
	.muted { color: var(--muted); }
	.small { font-size: 0.8rem; margin: 0; }
	.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
	.editor { display: grid; grid-template-columns: 312px minmax(0, 1fr) 420px; min-height: calc(100vh - var(--header-h, 4.4rem)); background: var(--bg); }
	.rail-col { border-right: var(--bw) solid var(--line); display: flex; flex-direction: column; background: var(--rail); }
	.rail-head { padding: 18px 20px 12px; display: flex; flex-direction: column; gap: 4px; border-bottom: var(--bw) solid var(--line); }
	.crumb { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--muted); }
	.crumb a { color: var(--accent); font-weight: 700; text-decoration: none; font-family: var(--tamil); }
	.saved.err { color: var(--bad); }
	.rail-head input { border: 0; background: none; padding: 2px 0; color: var(--ink); width: 100%; min-width: 0; }
	.rail-head input:focus-visible { outline: 0; box-shadow: 0 2px 0 var(--accent); }
	.title { font-family: var(--tamil); font-size: 1.35rem; font-weight: 600; line-height: 1.25; }
	.subrow { display: flex; align-items: baseline; gap: 4px; font-size: 0.82rem; color: var(--muted); }
	.subtitle { font-size: 0.82rem; color: var(--muted); flex: 1; }
	.n { white-space: nowrap; }
	.rail-body { padding: 12px 14px; overflow: auto; flex: 1; }
	.centre { min-width: 0; display: flex; flex-direction: column; background: var(--surface-2); }
	.toolbar { display: flex; align-items: center; gap: 8px; padding: 12px 24px; border-bottom: var(--bw) solid var(--line); flex-wrap: wrap; }
	.toolbar .kicker { letter-spacing: 0.08em; font-family: var(--tamil); text-transform: none; }
	.grow { flex: 1; }
	.toolbar .chip { min-height: 38px; font-size: 0.82rem; padding: 0.4rem 0.8rem; border-radius: 10px; }
	.toolbar .chip [lang='ta'] { font-family: var(--tamil); }
	.ver-label { position: relative; }
	.ver { appearance: auto; padding-right: 0.6rem; }
	.present { gap: 0.5rem; }
	.present .play { font-size: 0.7rem; }
	.present kbd { font: 600 0.68rem var(--sans); opacity: 0.75; border: 1px solid currentColor; border-radius: 4px; padding: 1px 5px; }
	.share-wrap { position: relative; }
	.share { position: absolute; right: 0; top: calc(100% + 8px); z-index: 20; width: min(24rem, 90vw); padding: 1rem; display: grid; gap: 0.7rem; box-shadow: var(--shadow); }
	.share .kicker { margin: 0; }
	.link { display: flex; gap: 6px; }
	.link input { flex: 1; min-width: 0; font: inherit; font-size: 0.82rem; padding: 0.5rem 0.7rem; border: var(--bw) solid var(--line-2); border-radius: var(--r-s); background: var(--surface-2); color: var(--ink); }
	.vis { display: grid; gap: 0.3rem; font-size: 0.9rem; }
	.vis [lang='ta'] { font-family: var(--tamil); }
	.canvas-wrap { padding: 24px 32px 0; }
	.canvas { width: 100%; aspect-ratio: 16 / 9; border-radius: 12px; border: var(--bw) solid var(--line); overflow: hidden; background: #0E1015; }
	.slide-title { display: grid; gap: 0.35rem; padding: 16px 32px 0; }
	.slide-title .kicker [lang='ta'] { font-family: var(--tamil); text-transform: none; letter-spacing: 0.06em; }
	.slide-title .field { font-size: 0.95rem; padding: 0.55rem 0.9rem; border-radius: var(--r); }
	.notes-wrap { flex: 1; min-height: 0; display: flex; flex-direction: column; padding: 16px 32px 24px; }
	.picker { border-left: var(--bw) solid var(--line); background: var(--rail); overflow: auto; }
	.toast { position: fixed; left: 50%; bottom: 1.5rem; transform: translateX(-50%); padding: 0.6rem 1rem; border-radius: 999px; background: var(--ink); color: var(--bg); font-size: 0.85rem; z-index: 40; }
	@media (max-width: 1180px) {
		.editor { grid-template-columns: 260px minmax(0, 1fr); }
		.picker { grid-column: 1 / -1; border-left: 0; border-top: var(--bw) solid var(--line); }
	}
	@media (max-width: 720px) {
		.editor { grid-template-columns: 1fr; }
		.rail-col { border-right: 0; border-bottom: var(--bw) solid var(--line); }
		.rail-body { max-height: 40vh; }
		.toolbar, .canvas-wrap, .slide-title, .notes-wrap { padding-left: 1rem; padding-right: 1rem; }
		.share { right: auto; left: 0; }
	}
</style>

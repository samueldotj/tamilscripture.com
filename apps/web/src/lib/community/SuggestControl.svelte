<script lang="ts">
	// "Suggest a correction" for one Tamil name or article paragraph. Renders
	// nothing until the client knows whether a session exists, so cached pages
	// are identical for every reader; signed-out readers get a sign-in link.
	import { page } from '$app/state';
	import { session } from '$lib/supabase/session.svelte';
	import { REASONS, formatReason, suggest } from './repo';
	import type { ReasonId } from './repo';

	let {
		target,
		current = '',
		source = '',
		lang,
		compact = false
	}: {
		/** `name:IRVTAM:Damascus` or `article:eastons/damascus#p1-…` */
		target: string;
		/** the Tamil text the reader sees now ('' when none yet) */
		current?: string;
		/** English source shown beside the field, for article paragraphs */
		source?: string;
		lang: 'ta' | 'en';
		compact?: boolean;
	} = $props();

	const ta = $derived(lang === 'ta');
	// Aquifer articles are CC BY-SA; a correction to them stays ShareAlike.
	const sharealike = $derived(target.startsWith('article:aquifer/'));
	let open = $state(false);
	let text = $state('');
	let reasonTag = $state<ReasonId | ''>('');
	let reason = $state('');
	let busy = $state(false);
	let done = $state(false);
	let error = $state('');

	function start() {
		text = current;
		reasonTag = '';
		reason = '';
		error = '';
		done = false;
		open = true;
	}
	async function submit(e: Event) {
		e.preventDefault();
		if (busy) return;
		busy = true;
		error = '';
		try {
			await suggest(target, current, text, formatReason(reasonTag, reason));
			done = true;
			open = false;
		} catch (err) {
			error = (err as Error).message;
		} finally {
			busy = false;
		}
	}
</script>

{#if session.ready}
	<div class="suggest" class:compact>
		{#if done}
			<span class="ok" lang={ta ? 'ta' : 'en'}>{ta ? 'நன்றி! உங்கள் பரிந்துரை மதிப்பாய்வுக்குச் சென்றது.' : 'Thank you! Your suggestion is waiting for review.'}</span>
		{:else if !session.signedIn}
			<a class="link" href="/signin?next={encodeURIComponent(page.url.pathname)}" lang={ta ? 'ta' : 'en'}>{ta ? 'திருத்தம் பரிந்துரைக்க உள்நுழையவும்' : 'Sign in to suggest a correction'}</a>
		{:else if !open}
			<button type="button" class="link" onclick={start} lang={ta ? 'ta' : 'en'}>{ta ? 'திருத்தம் பரிந்துரை' : 'Suggest a correction'}</button>
		{:else}
			<form class="form" onsubmit={submit}>
				{#if source}
					<div class="block">
						<div class="blabel" lang={ta ? 'ta' : 'en'}>{ta ? 'ஆங்கில மூலம்' : 'English source'}</div>
						<p class="src" lang="en">{source}</p>
					</div>
				{/if}
				{#if current}
					<div class="block">
						<div class="blabel" lang={ta ? 'ta' : 'en'}>{ta ? 'தற்போதைய தமிழ்' : 'Current Tamil'}</div>
						<p class="cur" lang="ta">{current}</p>
					</div>
				{/if}
				<label>
					<span lang={ta ? 'ta' : 'en'}>{ta ? (current ? 'உங்கள் திருத்தம்' : 'உங்கள் தமிழாக்கம்') : current ? 'Your correction' : 'Your Tamil translation'}</span>
					<textarea bind:value={text} lang="ta" rows={compact ? 1 : 4} required maxlength="4000"></textarea>
				</label>
				<div class="reasons">
					<span class="blabel" id="{target}-why" lang={ta ? 'ta' : 'en'}>{ta ? 'காரணம்' : 'Reason'}</span>
					<div class="chips" role="group" aria-labelledby="{target}-why">
						{#each REASONS as r (r.id)}
							<button
								type="button"
								class="rchip"
								class:on={reasonTag === r.id}
								aria-pressed={reasonTag === r.id}
								onclick={() => (reasonTag = reasonTag === r.id ? '' : r.id)}
								lang={ta ? 'ta' : 'en'}
							>{ta ? r.ta : r.en}</button>
						{/each}
					</div>
				</div>
				<label>
					<span lang={ta ? 'ta' : 'en'}>{ta ? 'விளக்கம் (விருப்பம்)' : 'Note (optional)'}</span>
					<input type="text" bind:value={reason} maxlength="500" lang={ta ? 'ta' : 'en'} />
				</label>
				<p class="consent" lang={ta ? 'ta' : 'en'}>
					{#if sharealike}
						{ta ? 'பரிந்துரைகள் மதிப்பாய்வுக்குப் பின்னரே வெளியிடப்படும்; இக்கட்டுரை CC BY-SA 4.0 என்பதால் உங்கள் பங்களிப்பும் CC BY-SA 4.0 உரிமத்தில் வெளியிடப்படும்.' : 'Suggestions are published only after review. This article is CC BY-SA 4.0, so your contribution is released under CC BY-SA 4.0 as well.'}
					{:else}
						{ta ? 'பரிந்துரைகள் மதிப்பாய்வுக்குப் பின்னரே வெளியிடப்படும்; உங்கள் பங்களிப்பு CC BY 4.0 உரிமத்தில் வெளியிடப்படும்.' : 'Suggestions are published only after review. Your contribution is released under CC BY 4.0.'}
					{/if}
				</p>
				{#if error}<p class="err" role="alert">{error}</p>{/if}
				<div class="row">
					<span class="wait" lang={ta ? 'ta' : 'en'}>{ta ? 'மதிப்பாய்வுக்குப் பின் வெளியிடப்படும்' : 'Published after review'}</span>
					<button type="submit" class="primary" disabled={busy || !text.trim()} lang={ta ? 'ta' : 'en'}>{ta ? 'அனுப்பு' : 'Send'}</button>
					<button type="button" onclick={() => (open = false)} lang={ta ? 'ta' : 'en'}>{ta ? 'ரத்து' : 'Cancel'}</button>
				</div>
			</form>
		{/if}
	</div>
{/if}

<style>
	.suggest { font-size: 0.82rem; margin-top: 0.3rem; }
	.link { background: none; border: 0; padding: 0; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; text-decoration: none; min-height: 32px; }
	.link[lang='ta'] { font-family: var(--tamil); }
	.ok { color: var(--muted); }
	.ok[lang='ta'] { font-family: var(--tamil); }
	.form { display: grid; gap: 0.6rem; padding: 0.8rem; border: 1px solid var(--line); border-radius: var(--r-s); background: var(--surface-2); margin-top: 0.4rem; max-width: 36rem; }
	/* The English source and the Tamil as it stands, so the reader corrects
	   against the original rather than from memory (design 8A). */
	.block { display: grid; gap: 0.2rem; }
	.blabel { color: var(--muted); font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em; }
	.blabel[lang='ta'] { font-family: var(--tamil); }
	.src { margin: 0; color: var(--ink-2); font-size: 0.85rem; line-height: 1.5; }
	.cur { margin: 0; font-family: var(--tamil); font-size: 0.95rem; line-height: 1.8; color: var(--ink-2); padding: 0.4rem 0.6rem; border-left: 2px solid var(--line-2); }
	.reasons { display: grid; gap: 0.3rem; }
	.reasons .chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
	.rchip { font: inherit; font-size: 0.8rem; font-weight: 600; padding: 0.3rem 0.7rem; border-radius: 999px; border: 1px solid var(--line-2); background: var(--surface); color: var(--ink-2); cursor: pointer; min-height: 32px; }
	.rchip[lang='ta'] { font-family: var(--tamil); }
	.rchip:hover { border-color: var(--accent); color: var(--accent); }
	.rchip.on { background: var(--accent); border-color: var(--accent); color: var(--on-accent); }
	label { display: grid; gap: 0.25rem; }
	label span { color: var(--muted); font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em; }
	label span[lang='ta'] { font-family: var(--tamil); }
	textarea, input { font: inherit; font-size: 1rem; padding: 0.5rem 0.7rem; border: 1px solid var(--line); border-radius: var(--r-s); background: var(--surface); color: inherit; width: 100%; box-sizing: border-box; }
	textarea[lang='ta'], input[lang='ta'] { font-family: var(--tamil); line-height: 1.7; }
	.consent { margin: 0; color: var(--muted); font-size: 0.75rem; line-height: 1.5; }
	.consent[lang='ta'] { font-family: var(--tamil); }
	.err { margin: 0; color: var(--bad); }
	.row { display: flex; gap: 0.5rem; align-items: center; }
	.wait { margin-right: auto; color: var(--muted); font-size: 0.75rem; }
	.wait[lang='ta'] { font-family: var(--tamil); }
	.row button { font: inherit; font-size: 0.85rem; font-weight: 600; padding: 0.45rem 0.9rem; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: inherit; cursor: pointer; min-height: 36px; }
	.row button[lang='ta'] { font-family: var(--tamil); }
	.row .primary { background: var(--ink); color: var(--surface); border-color: var(--ink); }
	.row button:disabled { opacity: 0.5; cursor: default; }
</style>

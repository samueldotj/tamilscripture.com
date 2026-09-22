<script lang="ts">
	// The last slide of every presentation, never stored: thanks, thumbs up or
	// down from the audience, and a share button. One vote per browser is
	// remembered locally; changing it moves the vote rather than adding one.
	import { votePresentation } from './repo';

	let {
		slug,
		title,
		subtitle = null,
		votes,
		shared = true,
		shareUrl,
		lang = 'ta'
	}: {
		slug: string;
		title: string;
		subtitle?: string | null;
		votes: { up: number; down: number };
		/** Only a presentation shared by link takes votes. */
		shared?: boolean;
		shareUrl: string;
		lang?: 'ta' | 'en';
	} = $props();

	const ta = $derived(lang === 'ta');
	const KEY = $derived(`ts-vote-${slug}`);
	let counts = $state({ up: 0, down: 0 });
	let mine = $state<boolean | null>(null);
	let busy = $state(false);
	let toast = $state('');
	$effect(() => { counts = { up: votes.up, down: votes.down }; });
	$effect(() => {
		try { const v = localStorage.getItem(KEY); mine = v === 'up' ? true : v === 'down' ? false : null; } catch { mine = null; }
	});

	async function vote(up: boolean) {
		if (busy || mine === up || !shared) return;
		busy = true;
		try {
			const r = await votePresentation(fetch, slug, up, mine);
			if (r) {
				counts = r;
				mine = up;
				try { localStorage.setItem(KEY, up ? 'up' : 'down'); } catch { /* private mode */ }
				flash(ta ? 'நன்றி!' : 'Thank you!');
			}
		} catch {
			flash(ta ? 'வாக்களிக்க முடியவில்லை' : 'Could not record the vote');
		} finally {
			busy = false;
		}
	}
	async function share() {
		if (navigator.share) {
			try { await navigator.share({ title, url: shareUrl }); return; } catch { /* cancelled */ return; }
		}
		try { await navigator.clipboard.writeText(shareUrl); flash(ta ? 'இணைப்பு நகலெடுக்கப்பட்டது' : 'Link copied'); } catch { flash(shareUrl); }
	}
	function flash(msg: string) { toast = msg; setTimeout(() => (toast = ''), 2000); }
</script>

<div class="closing">
	<p class="thanks" lang="ta">நன்றி <span class="en">· Thank you</span></p>
	{#if title}<h2 class="title" lang={/[஀-௿]/.test(title) ? 'ta' : 'en'}>{title}</h2>{/if}
	{#if subtitle}<p class="sub">{subtitle}</p>{/if}

	<p class="ask" lang={ta ? 'ta' : 'en'}>{ta ? 'இந்த விளக்கக்காட்சி உதவியதா?' : 'Was this presentation helpful?'}</p>
	<div class="votes" role="group" aria-label={ta ? 'வாக்கு' : 'Vote'}>
		<button type="button" class="vote up" class:on={mine === true} disabled={busy || !shared} aria-pressed={mine === true} onclick={() => vote(true)}>
			<span class="thumb" aria-hidden="true">👍</span>
			<span class="n">{counts.up}</span>
		</button>
		<button type="button" class="vote down" class:on={mine === false} disabled={busy || !shared} aria-pressed={mine === false} onclick={() => vote(false)}>
			<span class="thumb" aria-hidden="true">👎</span>
			<span class="n">{counts.down}</span>
		</button>
	</div>
	{#if !shared}
		<p class="note" lang={ta ? 'ta' : 'en'}>{ta ? 'வாக்குகள் பகிரப்பட்ட விளக்கக்காட்சிகளில் மட்டும் · “பகிர்” இல் “இணைப்பு உள்ள யாரும்” தேர்வு செய்யவும்' : 'Votes are taken on shared presentations only · choose “Anyone with the link” under Share'}</p>
	{/if}

	<button type="button" class="share" onclick={share}>
		<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v13"/><path d="m7 8 5-5 5 5"/><path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/></svg>
		<span lang={ta ? 'ta' : 'en'}>{ta ? 'பகிர்' : 'Share'}</span>
	</button>
	<p class="link">{shareUrl.replace(/^https?:\/\//, '')}</p>
	{#if toast}<p class="toast" role="status">{toast}</p>{/if}
</div>

<style>
	.closing { container-type: size; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; gap: 1.6cqmax; padding: 4cqmax 8cqmax 8cqmax; background: #0E1015; color: #F1ECE1; --accent: #D9B25C; }
	.thanks { margin: 0; font-family: var(--tamil); font-size: 2cqmax; letter-spacing: 0.12em; color: var(--accent); font-weight: 700; }
	.thanks .en { font-family: var(--sans); font-weight: 600; color: #B0AA9D; letter-spacing: 0.08em; }
	.title { margin: 0; font-size: 4cqmax; font-weight: 600; line-height: 1.25; text-wrap: balance; }
	.title[lang='ta'] { font-family: var(--tamil); }
	.sub { margin: 0; font-size: 1.6cqmax; color: #B0AA9D; }
	.ask { margin: 1cqmax 0 0; font-size: 1.9cqmax; color: #C4BEB1; }
	.ask[lang='ta'] { font-family: var(--tamil); }
	.votes { display: flex; gap: 2.4cqmax; }
	.vote { display: flex; flex-direction: column; align-items: center; gap: 0.4cqmax; min-width: 12cqmax; padding: 1.6cqmax 2cqmax; border-radius: 2cqmax; border: 0.2cqmax solid #3A3F4A; background: #20232A; color: #F1ECE1; cursor: pointer; transition: transform 0.12s ease, border-color 0.12s ease; }
	.vote:hover:not(:disabled) { border-color: var(--accent); transform: translateY(-0.3cqmax); }
	.vote.on { border-color: var(--accent); background: rgba(217, 178, 92, 0.14); }
	.vote:disabled { opacity: 0.55; cursor: default; }
	.thumb { font-size: 5cqmax; line-height: 1; }
	.n { font-family: var(--sans); font-size: 2.2cqmax; font-weight: 700; }
	.note { margin: 0; max-width: 70cqmax; font-size: 1.3cqmax; color: #7E8798; }
	.note[lang='ta'] { font-family: var(--tamil); }
	.share { margin-top: 1cqmax; display: inline-flex; align-items: center; gap: 0.8cqmax; padding: 1.1cqmax 2.4cqmax; border-radius: 1.4cqmax; border: 0; background: var(--accent); color: #1B1D22; font-size: 1.7cqmax; font-weight: 700; cursor: pointer; }
	.share [lang='ta'] { font-family: var(--tamil); }
	.share:hover { background: #E5C578; }
	.share svg { width: 1.8cqmax; height: 1.8cqmax; }
	.link { margin: 0; font-family: var(--sans); font-size: 1.3cqmax; color: #7E8798; letter-spacing: 0.02em; overflow-wrap: anywhere; }
	.toast { position: absolute; bottom: 12cqmax; margin: 0; padding: 0.7cqmax 1.4cqmax; border-radius: 999px; background: rgba(32, 35, 42, 0.92); border: 1px solid #3A3F4A; font-size: 1.3cqmax; color: #F1ECE1; font-family: var(--tamil); }
	@media (prefers-reduced-motion: reduce) { .vote { transition: none; } }
</style>

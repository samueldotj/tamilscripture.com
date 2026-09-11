<script lang="ts">
	// Bottom sheet for writing a note on the selected verses. Autosaves.
	import type { Note } from '$lib/personal/repo';
	import { saveNote, deleteNote } from '$lib/personal/repo';

	let {
		book,
		chapter,
		verseStart,
		verseEnd,
		existing = null,
		label,
		lang,
		onclose,
		onsaved
	}: {
		book: string;
		chapter: number;
		verseStart: number;
		verseEnd: number;
		existing?: Note | null;
		label: string;
		lang: 'ta' | 'en';
		onclose: () => void;
		onsaved: (note: Note | null) => void;
	} = $props();

	const ta = $derived(lang === 'ta');
	// The sheet is mounted per note, so the initial values are all it needs.
	// svelte-ignore state_referenced_locally
	let body = $state(existing?.body ?? '');
	// svelte-ignore state_referenced_locally
	let id = $state<string | undefined>(existing?.id);
	let status = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let timer: ReturnType<typeof setTimeout> | undefined;

	function schedule() {
		clearTimeout(timer);
		timer = setTimeout(save, 800);
	}
	async function save() {
		status = 'saving';
		try {
			if (!body.trim()) {
				if (id) { await deleteNote(id); id = undefined; onsaved(null); }
				status = 'idle';
				return;
			}
			const n = await saveNote({ id, book, chapter, verse_start: verseStart, verse_end: verseEnd, body });
			id = n.id;
			onsaved(n);
			status = 'saved';
		} catch {
			status = 'error';
		}
	}
	async function close() {
		clearTimeout(timer);
		await save();
		onclose();
	}
</script>

<div class="sheet" role="dialog" aria-label={ta ? 'குறிப்பு' : 'Note'} tabindex="-1">
	<span class="grab" aria-hidden="true"></span>
	<header>
		<div>
			<div class="kicker" lang={lang}>{ta ? 'குறிப்பு' : 'Note'}</div>
			<strong lang={lang}>{label}</strong>
		</div>
		<span class="status" role="status">
			{#if status === 'saving'}{ta ? 'சேமிக்கிறது…' : 'Saving…'}{:else if status === 'saved'}{ta ? 'சேமிக்கப்பட்டது' : 'Saved'}{:else if status === 'error'}{ta ? 'சேமிக்க முடியவில்லை' : 'Could not save'}{/if}
		</span>
		<button type="button" class="close" onclick={close} aria-label={ta ? 'மூடு' : 'Close'}>✕</button>
	</header>
	<!-- svelte-ignore a11y_autofocus -->
	<textarea class="field" bind:value={body} oninput={schedule} maxlength="5000" rows="6" lang={lang} placeholder={ta ? 'உங்கள் குறிப்பு…' : 'Your note…'} autofocus></textarea>
	<footer>
		<span class="count">{body.length} / 5000</span>
		{#if id}<button type="button" class="chip danger" onclick={async () => { body = ''; await save(); onclose(); }}>{ta ? 'நீக்கு' : 'Delete'}</button>{/if}
	</footer>
</div>

<style>
	.sheet { position: fixed; z-index: 22; left: 50%; bottom: 0; transform: translateX(-50%); width: min(40rem, 100%); background: var(--surface); border: var(--bw) solid var(--line-2); border-bottom: 0; border-radius: 26px 26px 0 0; padding: 0.7rem 1.25rem calc(1.1rem + env(safe-area-inset-bottom)); box-shadow: var(--shadow-lg); }
	.grab { display: block; width: 44px; height: 5px; border-radius: 999px; background: var(--line-2); margin: 0 auto 0.8rem; }
	header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.7rem; }
	header strong { font-size: 1.1rem; }
	header strong[lang='ta'], .kicker[lang='ta'] { font-family: var(--tamil); }
	.status { color: var(--muted); font-size: 0.85rem; margin-left: auto; }
	.close { flex: none; width: 40px; height: 40px; border-radius: 999px; border: 0; background: var(--surface-2); color: var(--ink-2); font-size: 0.95rem; cursor: pointer; }
	textarea.field { line-height: 1.7; resize: vertical; background: var(--bg); border-radius: 14px; }
	footer { display: flex; justify-content: space-between; align-items: center; margin-top: 0.6rem; font-size: 0.8rem; color: var(--muted); }
	.danger { color: var(--amber); min-height: 40px; }
</style>

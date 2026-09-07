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
	<header>
		<strong lang={lang}>{label}</strong>
		<span class="status" role="status">
			{#if status === 'saving'}{ta ? 'சேமிக்கிறது…' : 'Saving…'}{:else if status === 'saved'}{ta ? 'சேமிக்கப்பட்டது' : 'Saved'}{:else if status === 'error'}{ta ? 'சேமிக்க முடியவில்லை' : 'Could not save'}{/if}
		</span>
		<button type="button" class="close" onclick={close} aria-label={ta ? 'மூடு' : 'Close'}>×</button>
	</header>
	<!-- svelte-ignore a11y_autofocus -->
	<textarea bind:value={body} oninput={schedule} maxlength="5000" rows="6" lang={lang} placeholder={ta ? 'உங்கள் குறிப்பு…' : 'Your note…'} autofocus></textarea>
	<footer>
		<span class="count">{body.length} / 5000</span>
		{#if id}<button type="button" class="danger" onclick={async () => { body = ''; await save(); onclose(); }}>{ta ? 'நீக்கு' : 'Delete'}</button>{/if}
	</footer>
</div>

<style>
	.sheet { position: fixed; z-index: 22; left: 50%; bottom: 0; transform: translateX(-50%); width: min(40rem, 100%); background: var(--surface); border: 1px solid var(--line); border-bottom: 0; border-radius: 12px 12px 0 0; padding: 0.8rem 1rem calc(1rem + env(safe-area-inset-bottom)); box-shadow: 0 -8px 30px rgba(0, 0, 0, 0.18); }
	header { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.5rem; }
	header strong { font-family: var(--tamil); }
	.status { color: var(--muted); font-size: 0.85rem; margin-left: auto; }
	.close { border: 0; background: none; font-size: 1.5rem; line-height: 1; cursor: pointer; color: var(--muted); min-width: 40px; min-height: 40px; }
	textarea { width: 100%; font: inherit; font-family: var(--tamil); line-height: 1.7; padding: 0.6rem 0.75rem; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: inherit; resize: vertical; }
	footer { display: flex; justify-content: space-between; align-items: center; margin-top: 0.4rem; font-size: 0.8rem; color: var(--muted); }
	.danger { border: 1px solid var(--line); background: none; color: var(--accent); border-radius: 6px; padding: 0.3rem 0.8rem; cursor: pointer; }
</style>

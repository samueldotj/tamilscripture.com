<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { profile, updateProfile, exportMyData, deleteMyAccount } from '$lib/personal/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let share = $state(true);
	let exported = $state<string | null>(null);
	let confirmText = $state('');
	let busy = $state(false);
	let error = $state('');

	onMount(async () => { const p = await profile(); share = p?.share_aggregates ?? true; });

	async function toggleShare() { share = !share; await updateProfile({ share_aggregates: share }); }
	async function doExport() {
		busy = true;
		try {
			const data = await exportMyData();
			exported = JSON.stringify(data, null, 2);
		} catch (e) { error = (e as Error).message; } finally { busy = false; }
	}
	async function copyExport() { if (exported) await navigator.clipboard.writeText(exported); }
	async function doDelete() {
		if (confirmText !== 'DELETE') return;
		busy = true;
		try { await deleteMyAccount(); goto('/', { replaceState: true }); }
		catch (e) { error = (e as Error).message; busy = false; }
	}
</script>

<svelte:head><title>{ta ? 'கணக்கு' : 'Account'} · Tamil Scripture</title></svelte:head>

<h1>{ta ? 'கணக்கு' : 'Account'}</h1>
<p class="who">{session.user?.email}</p>

<section>
	<h2>{ta ? 'சமூகப் புள்ளிவிவரம்' : 'Community statistics'}</h2>
	<label><input type="checkbox" checked={share} onchange={toggleShare} /> {ta ? 'எனது அடிக்கோடுகளை அநாமதேய எண்ணிக்கையில் சேர்க்கவும் (யார் என்பது ஒருபோதும் காட்டப்படாது)' : 'Count my highlights in the anonymous verse statistics (who highlighted is never shown)'}</label>
</section>

<section>
	<h2>{ta ? 'தரவை ஏற்றுமதி செய்' : 'Export your data'}</h2>
	<p class="muted">{ta ? 'உங்கள் அடிக்கோடுகள், குறிப்புகள், வரலாறு ஒரு JSON ஆக.' : 'Your highlights, notes and history as one JSON document.'}</p>
	<button type="button" onclick={doExport} disabled={busy}>{ta ? 'ஏற்றுமதி' : 'Export'}</button>
	{#if exported}
		<button type="button" onclick={copyExport}>{ta ? 'நகல்' : 'Copy'}</button>
		<textarea readonly rows="8">{exported}</textarea>
	{/if}
</section>

<section class="danger">
	<h2>{ta ? 'கணக்கை நீக்கு' : 'Delete account'}</h2>
	<p class="muted">{ta ? 'உங்கள் எல்லா தனிப்பட்ட தரவும் உடனே நீக்கப்படும். மீட்க முடியாது. உறுதிப்படுத்த DELETE என தட்டச்சு செய்யவும்.' : 'All your personal data is removed immediately and cannot be recovered. Type DELETE to confirm.'}</p>
	<input type="text" bind:value={confirmText} autocomplete="off" aria-label="Type DELETE to confirm" />
	<button type="button" class="del" onclick={doDelete} disabled={busy || confirmText !== 'DELETE'}>{ta ? 'கணக்கை நீக்கு' : 'Delete my account'}</button>
</section>

{#if error}<p class="err" role="alert">{error}</p>{/if}

<style>
	h1 { font-family: var(--tamil); font-size: 1.5rem; margin: 0; }
	.who { color: var(--muted); margin: 0.2rem 0 1.5rem; }
	section { max-width: 40rem; padding: 1rem 0 1.4rem; border-top: 1px solid var(--line); }
	h2 { font-family: var(--tamil); font-size: 1.05rem; margin: 0 0 0.5rem; }
	label { display: flex; gap: 0.6rem; align-items: flex-start; font-family: var(--tamil); }
	.muted { color: var(--muted); }
	button, input[type='text'] { font: inherit; padding: 0.5rem 0.9rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; min-height: 40px; }
	button { cursor: pointer; font-family: var(--tamil); }
	button:disabled { opacity: 0.5; cursor: default; }
	.del { border-color: var(--accent); color: var(--accent); }
	textarea { display: block; width: 100%; margin-top: 0.6rem; font: 0.8rem ui-monospace, monospace; padding: 0.6rem; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: inherit; }
	.err { color: var(--accent); }
</style>

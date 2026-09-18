<script lang="ts">
	// Moderators appoint and remove reviewers. Moderators themselves are set
	// by the owner in the database; set_role refuses anything else.
	import { onMount, getContext } from 'svelte';
	import { listStaff, setRole, setRoleByEmail, type Role, type StaffMember } from '$lib/community/repo';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	const roleBox = getContext<{ readonly value: Role | null }>('mod-role');
	const isModerator = $derived(roleBox?.value === 'moderator');
	let staff = $state<StaffMember[]>([]);
	let email = $state('');
	let msg = $state('');
	let err = $state('');
	let loading = $state(true);

	async function load() {
		try { staff = await listStaff(); } catch (e) { err = (e as Error).message; } finally { loading = false; }
	}
	onMount(load);

	async function appoint(e: Event) {
		e.preventDefault();
		msg = ''; err = '';
		try {
			await setRoleByEmail(email.trim(), 'reviewer');
			msg = ta ? `${email.trim()} இப்போது மதிப்பாய்வாளர்.` : `${email.trim()} is now a reviewer.`;
			email = '';
			await load();
		} catch (e2) { err = (e2 as Error).message; }
	}
	async function remove(m: StaffMember) {
		msg = ''; err = '';
		try { await setRole(m.user_id, 'reader'); await load(); } catch (e) { err = (e as Error).message; }
	}
</script>

<svelte:head><title>{ta ? 'பங்குகள்' : 'Roles'} · Tamil Scripture</title></svelte:head>

<h1 lang={ta ? 'ta' : 'en'}>{ta ? 'பங்குகள்' : 'Roles'}</h1>

{#if !isModerator}
	<p class="muted" lang={ta ? 'ta' : 'en'}>{ta ? 'மதிப்பீட்டாளர்களுக்கு மட்டும்.' : 'Moderators only.'}</p>
{:else}
	<form class="appoint" onsubmit={appoint}>
		<label><span lang={ta ? 'ta' : 'en'}>{ta ? 'மதிப்பாய்வாளராக நியமிக்க மின்னஞ்சல்' : 'Email of the account to make a reviewer'}</span>
			<input type="email" bind:value={email} required placeholder="name@example.com" /></label>
		<button type="submit" class="primary" lang={ta ? 'ta' : 'en'}>{ta ? 'நியமி' : 'Appoint'}</button>
	</form>
	<p class="muted small" lang={ta ? 'ta' : 'en'}>{ta ? 'அந்த நபர் முதலில் தளத்தில் ஒருமுறை உள்நுழைந்திருக்க வேண்டும்.' : 'The person must have signed in to the site at least once.'}</p>
	{#if err}<p class="err" role="alert">{err}</p>{/if}
	{#if msg}<p class="ok">{msg}</p>{/if}

	{#if loading}
		<p class="muted">…</p>
	{:else}
		<table>
			<thead><tr><th lang={ta ? 'ta' : 'en'}>{ta ? 'பெயர்' : 'Name'}</th><th>Email</th><th lang={ta ? 'ta' : 'en'}>{ta ? 'பங்கு' : 'Role'}</th><th></th></tr></thead>
			<tbody>
				{#each staff as m (m.user_id)}
					<tr>
						<td>{m.display_name ?? '—'}</td>
						<td>{m.email}</td>
						<td>{m.role}</td>
						<td>{#if m.role === 'reviewer'}<button type="button" onclick={() => remove(m)} lang={ta ? 'ta' : 'en'}>{ta ? 'நீக்கு' : 'Remove'}</button>{/if}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
{/if}

<style>
	h1 { font-size: 1.5rem; margin: 0 0 1rem; }
	h1[lang='ta'], label span[lang='ta'], button[lang='ta'], th[lang='ta'], .muted[lang='ta'] { font-family: var(--tamil); }
	.appoint { display: flex; flex-wrap: wrap; gap: 0.7rem; align-items: end; max-width: 40rem; }
	.appoint label { display: grid; gap: 0.25rem; flex: 1; min-width: 16rem; }
	.appoint label span { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	input { font: inherit; padding: 0.5rem 0.7rem; border: 1px solid var(--line); border-radius: var(--r-s); background: var(--surface); color: inherit; min-height: 42px; }
	button { font: inherit; font-size: 0.85rem; font-weight: 600; padding: 0.5rem 1rem; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); color: inherit; cursor: pointer; min-height: 40px; }
	.primary { background: var(--ink); color: var(--surface); border-color: var(--ink); }
	table { border-collapse: collapse; margin-top: 1.2rem; max-width: 48rem; width: 100%; }
	th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--line); font-size: 0.92rem; }
	th { font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }
	.muted { color: var(--muted); margin: 0.5rem 0 0; }
	.small { font-size: 0.8rem; }
	.err { color: var(--bad); }
	.ok { color: var(--good); }
</style>

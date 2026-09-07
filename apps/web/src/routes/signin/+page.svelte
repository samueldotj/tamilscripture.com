<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	const next = $derived(page.url.searchParams.get('next') || '/');
	let email = $state('');
	let sent = $state(false);
	let busy = $state(false);
	let error = $state('');

	$effect(() => {
		if (session.ready && session.signedIn) goto(next, { replaceState: true });
	});

	async function magic(e: Event) {
		e.preventDefault();
		error = '';
		busy = true;
		try {
			await session.signInWithEmail(email.trim(), next);
			sent = true;
		} catch (err) {
			error = (err as Error).message;
		} finally {
			busy = false;
		}
	}
	async function google() {
		error = '';
		try { await session.signInWithGoogle(next); } catch (err) { error = (err as Error).message; }
	}
</script>

<svelte:head>
	<title>{ta ? 'உள்நுழை' : 'Sign in'} · Tamil Scripture</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<section class="signin">
	<h1>{ta ? 'உள்நுழை' : 'Sign in'}</h1>
	<p class="why">{ta ? 'வாசிப்பதற்கு கணக்கு தேவையில்லை. உள்நுழைந்தால் உங்கள் வாசிப்பு வரலாறு, குறிப்புகள், அடிக்கோடிடல்கள் சாதனங்களுக்கு இடையே சேமிக்கப்படும்.' : 'No account is needed to read. Signing in keeps your history, notes and highlights across devices.'}</p>

	{#if sent}
		<p class="ok" role="status">{ta ? `${email} க்கு ஒரு இணைப்பு அனுப்பப்பட்டது. அதைத் திறந்தால் உள்நுழைவீர்கள்.` : `We sent a link to ${email}. Open it to finish signing in.`}</p>
	{:else}
		<form onsubmit={magic}>
			<label for="email">{ta ? 'மின்னஞ்சல்' : 'Email'}</label>
			<input id="email" type="email" bind:value={email} required autocomplete="email" inputmode="email" placeholder="you@example.com" />
			<button type="submit" disabled={busy}>{ta ? 'இணைப்பை அனுப்பு' : 'Send sign-in link'}</button>
		</form>
		<div class="or"><span>{ta ? 'அல்லது' : 'or'}</span></div>
		<button type="button" class="google" onclick={google}>
			<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.5l6.7-6.7C35.6 2.6 30.2 0 24 0 14.6 0 6.5 5.4 2.5 13.3l7.8 6C12.2 13.6 17.6 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.4 5.7c4.3-4 7.2-9.9 7.2-17.4z"/><path fill="#FBBC05" d="M10.3 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.8-6A24 24 0 0 0 0 24c0 3.9.9 7.5 2.5 10.7l7.8-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.9 2.3-8.5 2.3-6.4 0-11.8-4.1-13.7-9.8l-7.8 6C6.5 42.6 14.6 48 24 48z"/></svg>
			{ta ? 'Google மூலம் உள்நுழை' : 'Continue with Google'}
		</button>
	{/if}
	{#if error}<p class="err" role="alert">{error}</p>{/if}
	<p class="privacy"><a href="/about">{ta ? 'தனியுரிமை' : 'Privacy'}</a></p>
</section>

<style>
	.signin { max-width: 26rem; margin: 2rem auto; }
	h1 { font-family: var(--tamil); font-size: 1.6rem; margin: 0 0 0.5rem; }
	.why { color: var(--muted); font-family: var(--tamil); }
	form { display: grid; gap: 0.5rem; margin-top: 1.5rem; }
	label { font-size: 0.85rem; color: var(--muted); }
	input { font: inherit; padding: 0.65rem 0.8rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: inherit; }
	button { font: inherit; padding: 0.65rem 1rem; border-radius: 6px; cursor: pointer; min-height: 44px; font-family: var(--tamil); }
	form button { border: 0; background: var(--accent); color: #fff; }
	form button:disabled { opacity: 0.6; }
	.or { display: flex; align-items: center; gap: 0.8rem; margin: 1.2rem 0; color: var(--muted); font-size: 0.85rem; }
	.or::before, .or::after { content: ''; flex: 1; border-top: 1px solid var(--line); }
	.google { width: 100%; display: flex; align-items: center; justify-content: center; gap: 0.6rem; border: 1px solid var(--line); background: var(--surface); color: inherit; }
	.ok { padding: 1rem; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); font-family: var(--tamil); }
	.err { color: var(--accent); }
	.privacy { margin-top: 2rem; font-size: 0.85rem; }
</style>

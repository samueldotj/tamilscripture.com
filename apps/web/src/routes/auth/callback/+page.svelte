<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { sb } from '$lib/supabase/client';
	import { session } from '$lib/supabase/session.svelte';
	import { settings } from '$lib/settings/store.svelte';

	const ta = $derived(settings.value.uiLang === 'ta');
	let message = $state('');
	let failed = $state(false);
	/** Set when the Android app started this sign-in: the code belongs to it, not to this browser. */
	let appLink = $state('');

	onMount(async () => {
		// The app holds the PKCE verifier, so the code goes back to it unexchanged
		// (tamilscripture.app design §13.1). Nothing else in the URL is passed on.
		if (page.url.searchParams.get('app') === '1') {
			const code = page.url.searchParams.get('code') ?? '';
			const err = page.url.searchParams.get('error_description') ?? '';
			const q = code ? `code=${encodeURIComponent(code)}` : `error=${encodeURIComponent(err || 'no code')}`;
			appLink = `tamilscripture://auth?${q}`;
			location.replace(appLink);
			return;
		}
		const next = page.url.searchParams.get('next') || '/';
		const target = next.startsWith('/') && !next.startsWith('//') ? next : '/';
		const code = page.url.searchParams.get('code');
		const err = page.url.searchParams.get('error_description');
		if (err) {
			failed = true;
			message = err;
			return;
		}
		try {
			const client = await sb();
			if (code) {
				const { error } = await client.auth.exchangeCodeForSession(code);
				if (error) {
					// A reload of this page, or a second tab, arrives with a code that
					// has already been used. If that first exchange signed us in,
					// carry on rather than report an error.
					const { data } = await client.auth.getSession();
					if (!data.session) throw error;
				}
			}
			await session.refresh();
			goto(target, { replaceState: true });
		} catch (e) {
			failed = true;
			const msg = (e as Error).message;
			// The code verifier lives in this browser's storage, so a sign-in link
			// opened in another browser or app cannot complete here.
			message = /code verifier/i.test(msg)
				? ta
					? 'இந்த உள்நுழைவு வேறு உலாவியில் தொடங்கப்பட்டது. தொடங்கிய அதே உலாவியில் இணைப்பைத் திறக்கவும், அல்லது இங்கே மீண்டும் உள்நுழையவும்.'
					: 'This sign-in was started in a different browser. Open the link in the browser you started from, or sign in again here.'
				: msg;
		}
	});
</script>

<svelte:head><title>Sign in · Tamil Scripture</title><meta name="robots" content="noindex" /></svelte:head>
<div class="wrap" role="status">
	{#if appLink}
		<p class="msg" lang={ta ? 'ta' : 'en'}>{ta ? 'பயன்பாட்டுக்குத் திரும்புகிறது…' : 'Returning to the app…'}</p>
		<p><a class="chip" href={appLink} lang={ta ? 'ta' : 'en'}>{ta ? 'தமிழ் வேதாகமம் பயன்பாட்டைத் திற' : 'Open the Tamil Scripture app'}</a></p>
	{:else if failed}
		<p class="msg" lang={ta ? 'ta' : 'en'}>{message}</p>
		<p><a class="chip" href="/signin" lang={ta ? 'ta' : 'en'}>{ta ? 'மீண்டும் உள்நுழை' : 'Sign in again'}</a></p>
	{:else}
		<p class="msg" lang={ta ? 'ta' : 'en'}>{ta ? 'உள்நுழைகிறது…' : 'Signing you in…'}</p>
	{/if}
</div>

<style>
	.wrap { padding: 2rem 0; max-width: 36rem; }
	.msg { color: var(--muted); margin: 0 0 1rem; line-height: 1.6; }
	.msg[lang='ta'] { font-family: var(--tamil); }
	.chip[lang='ta'] { font-family: var(--tamil); }
</style>

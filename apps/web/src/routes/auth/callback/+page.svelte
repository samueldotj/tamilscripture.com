<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { sb } from '$lib/supabase/client';
	import { session } from '$lib/supabase/session.svelte';

	let message = $state('Signing you in…');

	onMount(async () => {
		const next = page.url.searchParams.get('next') || '/';
		const code = page.url.searchParams.get('code');
		const err = page.url.searchParams.get('error_description');
		if (err) { message = err; return; }
		try {
			if (code) {
				const client = await sb();
				const { error } = await client.auth.exchangeCodeForSession(code);
				if (error) throw error;
			}
			await session.refresh();
			// Only allow same-site targets.
			goto(next.startsWith('/') && !next.startsWith('//') ? next : '/', { replaceState: true });
		} catch (e) {
			message = (e as Error).message;
		}
	});
</script>

<svelte:head><title>Sign in · Tamil Scripture</title><meta name="robots" content="noindex" /></svelte:head>
<p class="msg" role="status">{message}</p>

<style>
	.msg { color: var(--muted); padding: 2rem 0; }
</style>

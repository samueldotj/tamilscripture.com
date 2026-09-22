<script lang="ts">
	// The editor is its own chunk, fetched when the page opens: the page node
	// itself stays a few hundred bytes (see .size-limit.json).
	import { onMount } from 'svelte';
	import type { Component } from 'svelte';
	import { page } from '$app/state';

	let Editor = $state<Component<{ slug: string }> | null>(null);
	onMount(async () => {
		Editor = (await import('$lib/present/Editor.svelte')).default;
	});
</script>

{#if Editor}
	<Editor slug={page.params.slug!} />
{:else}
	<p class="wait" aria-busy="true">…</p>
{/if}

<style>
	.wait { color: var(--muted); padding: 2rem; }
</style>

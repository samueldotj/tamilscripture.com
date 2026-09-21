<script lang="ts">
	// Text with its verse references as links (see linkify.ts). The links point
	// at the reader's own version; the site-wide hover preview shows the verse.
	import { settings } from '$lib/settings/store.svelte';
	import { linkRefs } from './linkify';

	let { text, version }: { text: string | null | undefined; version?: string } = $props();
	const pieces = $derived(linkRefs(text ?? '', (version ?? settings.value.version).toLowerCase()));
</script>

{#each pieces as p, i (i)}{#if p.href}<a class="ref-link" href={p.href}>{p.t}</a>{:else}{p.t}{/if}{/each}

<style>
	.ref-link { color: var(--accent); text-decoration: underline dotted; text-underline-offset: 0.2em; }
	.ref-link:hover { text-decoration-style: solid; }
</style>

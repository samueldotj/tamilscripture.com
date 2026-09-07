<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<header class="site">
	<a class="brand" href="/">
		<span class="ta">தமிழ் வேதாகமம்</span>
		<span class="en">tamilscripture.com</span>
	</a>
</header>

<main class="page">
	{@render children()}
</main>

<style>
	.site { border-bottom: 1px solid var(--line); background: var(--surface); }
	.brand { display: flex; align-items: baseline; gap: 0.75rem; max-width: 60rem; margin: 0 auto; padding: 0.75rem 1rem; text-decoration: none; color: inherit; }
	.brand .ta { font-family: var(--tamil); font-weight: 600; font-size: 1.1rem; }
	.brand .en { font-size: 0.8rem; color: var(--muted); letter-spacing: 0.04em; }
	.page { max-width: 60rem; margin: 0 auto; padding: 1.25rem 1rem 4rem; }
</style>

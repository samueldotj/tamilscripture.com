<script lang="ts">
	import ChapterPage from '$lib/reader/ChapterPage.svelte';
	let { data } = $props();
</script>

<ChapterPage {data} />

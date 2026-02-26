<script>
	import '../app.css';
	import NavBar from '../components/NavBar.svelte';
	import { activePage } from '$lib/stores.js';
	import { page } from '$app/stores';

	// Sync active page from route
	$: {
		const path = $page.url.pathname;
		if (path === '/') activePage.set('chat');
		else if (path.startsWith('/dashboard')) activePage.set('dashboard');
		else if (path.startsWith('/service')) activePage.set('service');
		else if (path.startsWith('/vehicle')) activePage.set('vehicle');
		else if (path.startsWith('/settings')) activePage.set('settings');
	}
</script>

<div class="app">
	<NavBar />
	<main>
		<slot />
	</main>
</div>

<style>
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}
	main {
		flex: 1;
		display: flex;
		flex-direction: column;
	}
</style>

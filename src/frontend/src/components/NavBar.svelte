<script>
	import { activePage } from '$lib/stores.js';

	const navItems = [
		{ id: 'chat', label: '> chat', href: '/' },
		{ id: 'dashboard', label: '> dash', href: '/dashboard' },
		{ id: 'service', label: '> svc', href: '/service' },
		{ id: 'vehicle', label: '> info', href: '/vehicle' },
		{ id: 'settings', label: '> sys', href: '/settings' }
	];
</script>

<nav class="navbar">
	<div class="brand">
		<span class="brand-name">AxleLore</span>
		<span class="brand-tag">FZJ80</span>
	</div>
	<div class="nav-links">
		{#each navItems as item}
			<a
				href={item.href}
				class="nav-link"
				class:active={$activePage === item.id}
			>
				{item.label}
			</a>
		{/each}
	</div>
</nav>

<style>
	.navbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 1rem;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 100;
	}
	.brand {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.brand-name {
		color: var(--green);
		font-weight: 700;
		font-size: 1rem;
	}
	.brand-tag {
		color: var(--amber);
		font-size: 0.7rem;
		border: 1px solid var(--amber-dim);
		padding: 0.1rem 0.35rem;
		border-radius: var(--radius);
	}
	.nav-links {
		display: flex;
		gap: 0.25rem;
	}
	.nav-link {
		color: var(--text-secondary);
		padding: 0.35rem 0.6rem;
		border-radius: var(--radius);
		font-size: 0.8rem;
		transition: all 0.15s;
	}
	.nav-link:hover {
		background: var(--bg-elevated);
		color: var(--text-primary);
		text-decoration: none;
	}
	.nav-link.active {
		color: var(--green);
		background: var(--green-bg);
	}

	@media (max-width: 600px) {
		.nav-links {
			gap: 0;
		}
		.nav-link {
			padding: 0.35rem 0.4rem;
			font-size: 0.75rem;
		}
	}
</style>

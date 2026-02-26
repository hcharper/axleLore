<script>
	import { onMount } from 'svelte';
	import { system, health } from '$lib/api.js';

	let deviceInfo = null;
	let versionInfo = null;
	let healthInfo = null;
	let loading = true;
	let error = '';

	onMount(async () => {
		try {
			[deviceInfo, versionInfo, healthInfo] = await Promise.all([
				system.device(),
				system.version(),
				health()
			]);
		} catch (err) {
			error = err.message;
		}
		loading = false;
	});
</script>

<div class="settings-page">
	<h2>System Info</h2>

	{#if error}
		<div class="error">{error}</div>
	{/if}

	{#if loading}
		<p class="loading">Loading...</p>
	{:else}
		{#if healthInfo}
			<div class="section">
				<h3>Health</h3>
				<div class="info-grid">
					<span class="label">Status</span>
					<span class="value ok">{healthInfo.status}</span>
					<span class="label">LLM</span>
					<span class="value" class:ok={healthInfo.services?.llm === 'ok'} class:warn={healthInfo.services?.llm !== 'ok'}>
						{healthInfo.services?.llm || 'unknown'}
					</span>
					<span class="label">Models</span>
					<span class="value">{(healthInfo.services?.llm_models || []).join(', ') || 'none'}</span>
					<span class="label">Vector Store</span>
					<span class="value">{healthInfo.services?.vector_store || 'unknown'}</span>
					<span class="label">OBD2</span>
					<span class="value">{JSON.stringify(healthInfo.services?.obd2) || 'disabled'}</span>
				</div>
			</div>
		{/if}

		{#if versionInfo}
			<div class="section">
				<h3>Version</h3>
				<div class="info-grid">
					<span class="label">Software</span>
					<span class="value">{versionInfo.software_version}</span>
					<span class="label">KB Pack</span>
					<span class="value">{versionInfo.kb_version}</span>
					<span class="label">Model</span>
					<span class="value">{versionInfo.model}</span>
					<span class="label">Fallback</span>
					<span class="value">{versionInfo.fallback_model}</span>
				</div>
			</div>
		{/if}

		{#if deviceInfo}
			<div class="section">
				<h3>Device</h3>
				<div class="info-grid">
					<span class="label">Device ID</span>
					<span class="value">{deviceInfo.device_id}</span>
					<span class="label">Hostname</span>
					<span class="value">{deviceInfo.hostname}</span>
					<span class="label">Hardware</span>
					<span class="value">{deviceInfo.hardware}</span>
					<span class="label">Provisioned</span>
					<span class="value" class:ok={deviceInfo.provisioned}>{deviceInfo.provisioned ? 'Yes' : 'No'}</span>
					<span class="label">Wi-Fi</span>
					<span class="value" class:ok={deviceInfo.wifi_configured}>{deviceInfo.wifi_configured ? 'Configured' : 'Not configured'}</span>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.settings-page { padding: 1rem; }
	h2 { margin-bottom: 1rem; }
	.error {
		padding: 0.5rem 0.75rem;
		background: var(--red-bg);
		color: var(--red);
		border: 1px solid var(--red);
		border-radius: var(--radius);
		margin-bottom: 1rem;
		font-size: 0.85rem;
	}
	.section {
		margin-bottom: 1.5rem;
		padding: 0.75rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
	}
	.section h3 {
		color: var(--amber);
		margin-bottom: 0.5rem;
		font-size: 0.9rem;
	}
	.info-grid {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.25rem 1rem;
		font-size: 0.85rem;
	}
	.label { color: var(--text-secondary); }
	.value { color: var(--text-primary); }
	.value.ok { color: var(--green); }
	.value.warn { color: var(--amber); }
	.loading { text-align: center; padding: 3rem 1rem; color: var(--text-secondary); }
</style>

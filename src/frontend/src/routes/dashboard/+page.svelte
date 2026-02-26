<script>
	import { onMount, onDestroy } from 'svelte';
	import { sensorData, obd2Connected } from '$lib/stores.js';
	import { obd2 } from '$lib/api.js';
	import { createOBD2Socket } from '$lib/ws.js';
	import SensorGauge from '../../components/SensorGauge.svelte';

	let ws = null;
	let error = '';
	let dtcs = [];

	onMount(async () => {
		try {
			const status = await obd2.status();
			obd2Connected.set(status.enabled && status.connected);
		} catch {
			// ignore
		}
	});

	function connectLive() {
		error = '';
		ws = createOBD2Socket(
			(data) => sensorData.set(data),
			(err) => { error = err; }
		);
	}

	function disconnectLive() {
		ws?.close();
		ws = null;
		sensorData.set(null);
	}

	async function readDTCs() {
		try {
			const res = await obd2.dtcs();
			dtcs = res.dtcs || [];
		} catch (err) {
			error = err.message;
		}
	}

	onDestroy(() => {
		ws?.close();
	});
</script>

<div class="dashboard">
	<div class="header">
		<h2>OBD-II Dashboard</h2>
		<div class="controls">
			{#if ws}
				<button on:click={disconnectLive}>Disconnect</button>
			{:else}
				<button class="primary" on:click={connectLive}>Connect Live</button>
			{/if}
			<button on:click={readDTCs}>Read DTCs</button>
		</div>
	</div>

	{#if error}
		<div class="error">{error}</div>
	{/if}

	<div class="gauges">
		<SensorGauge
			label="RPM" unit="rpm"
			value={$sensorData?.rpm}
			min={0} max={6000}
			warnAt={4500} critAt={5500}
		/>
		<SensorGauge
			label="Speed" unit="mph"
			value={$sensorData?.speed_mph}
			min={0} max={120}
		/>
		<SensorGauge
			label="Coolant" unit="F"
			value={$sensorData?.coolant_temp_f}
			min={100} max={260}
			warnAt={220} critAt={240}
		/>
		<SensorGauge
			label="Throttle" unit="%"
			value={$sensorData?.throttle_pct}
			min={0} max={100}
		/>
		<SensorGauge
			label="Load" unit="%"
			value={$sensorData?.engine_load_pct}
			min={0} max={100}
			warnAt={85} critAt={95}
		/>
		<SensorGauge
			label="Intake" unit="F"
			value={$sensorData?.intake_temp_f}
			min={0} max={200}
			warnAt={150} critAt={180}
		/>
	</div>

	{#if dtcs.length > 0}
		<div class="dtc-panel">
			<h3>Diagnostic Trouble Codes</h3>
			{#each dtcs as dtc}
				<div class="dtc">
					<span class="dtc-code">{dtc.code}</span>
					<span class="dtc-desc">{dtc.description}</span>
					<span class="dtc-status {dtc.status}">{dtc.status}</span>
				</div>
			{/each}
		</div>
	{/if}

	{#if !$sensorData && !error}
		<div class="empty">
			<p>Connect to the OBD-II adapter to see live engine data.</p>
			<p class="hint">Requires an ELM327 adapter connected to the vehicle's OBD-II port.</p>
		</div>
	{/if}
</div>

<style>
	.dashboard {
		padding: 1rem;
	}
	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}
	.controls {
		display: flex;
		gap: 0.5rem;
	}
	.gauges {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
		gap: 1rem;
		justify-items: center;
		padding: 1rem 0;
	}
	.error {
		padding: 0.5rem 0.75rem;
		background: var(--red-bg);
		color: var(--red);
		border: 1px solid var(--red);
		border-radius: var(--radius);
		margin-bottom: 1rem;
		font-size: 0.85rem;
	}
	.dtc-panel {
		margin-top: 1.5rem;
		padding: 1rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
	}
	.dtc-panel h3 {
		color: var(--amber);
		margin-bottom: 0.5rem;
	}
	.dtc {
		display: flex;
		gap: 1rem;
		padding: 0.35rem 0;
		border-bottom: 1px solid var(--border);
		font-size: 0.85rem;
	}
	.dtc-code {
		color: var(--red);
		font-weight: 700;
		min-width: 5ch;
	}
	.dtc-desc { flex: 1; }
	.dtc-status {
		font-size: 0.75rem;
		padding: 0.1rem 0.4rem;
		border-radius: var(--radius);
	}
	.dtc-status.active { background: var(--red-bg); color: var(--red); }
	.dtc-status.pending { background: var(--amber-bg); color: var(--amber); }
	.dtc-status.cleared { background: var(--green-bg); color: var(--green); }
	.empty {
		text-align: center;
		padding: 3rem 1rem;
		color: var(--text-secondary);
	}
	.hint {
		font-size: 0.8rem;
		color: var(--text-muted);
		margin-top: 0.5rem;
	}
</style>

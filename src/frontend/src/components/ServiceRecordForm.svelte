<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let vehicleId;

	let serviceDate = new Date().toISOString().slice(0, 10);
	let serviceType = 'oil_change';
	let mileage = '';
	let description = '';
	let cost = '';
	let performedBy = 'self';
	let loading = false;

	const serviceTypes = [
		'oil_change', 'tire_rotation', 'timing_belt', 'spark_plugs',
		'brake_service', 'transmission_service', 'coolant_flush',
		'differential_service', 'suspension', 'electrical', 'other'
	];

	async function handleSubmit() {
		loading = true;
		const data = {
			service_date: new Date(serviceDate).toISOString(),
			service_type: serviceType,
			mileage: mileage ? parseInt(mileage) : null,
			description: description || null,
			cost: cost ? parseFloat(cost) : null,
			performed_by: performedBy
		};
		dispatch('create', data);
		loading = false;
	}
</script>

<form class="service-form" on:submit|preventDefault={handleSubmit}>
	<h3>Log Service</h3>

	<div class="field">
		<label for="service-type">Type</label>
		<select id="service-type" bind:value={serviceType}>
			{#each serviceTypes as t}
				<option value={t}>{t.replace(/_/g, ' ')}</option>
			{/each}
		</select>
	</div>

	<div class="row">
		<div class="field">
			<label for="service-date">Date</label>
			<input id="service-date" type="date" bind:value={serviceDate} />
		</div>
		<div class="field">
			<label for="mileage">Mileage</label>
			<input id="mileage" type="number" bind:value={mileage} placeholder="mi" />
		</div>
	</div>

	<div class="field">
		<label for="description">Notes</label>
		<textarea id="description" bind:value={description} rows="2" placeholder="Details..."></textarea>
	</div>

	<div class="row">
		<div class="field">
			<label for="cost">Cost ($)</label>
			<input id="cost" type="number" step="0.01" bind:value={cost} />
		</div>
		<div class="field">
			<label for="performed-by">By</label>
			<select id="performed-by" bind:value={performedBy}>
				<option value="self">Self</option>
				<option value="mechanic">Mechanic</option>
				<option value="dealer">Dealer</option>
			</select>
		</div>
	</div>

	<button type="submit" class="primary" disabled={loading}>
		{loading ? 'Saving...' : '+ Log Record'}
	</button>
</form>

<style>
	.service-form {
		padding: 1rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
	}
	h3 {
		margin-bottom: 0.75rem;
		color: var(--amber);
	}
	.field {
		margin-bottom: 0.5rem;
		flex: 1;
	}
	.field label {
		display: block;
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-bottom: 0.2rem;
	}
	.row {
		display: flex;
		gap: 0.75rem;
	}
	button {
		margin-top: 0.5rem;
		width: 100%;
	}
</style>

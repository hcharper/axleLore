<script>
	import { onMount } from 'svelte';
	import { currentVehicle } from '$lib/stores.js';
	import { service, vehicles } from '$lib/api.js';
	import ServiceRecordForm from '../../components/ServiceRecordForm.svelte';

	let records = [];
	let vehicleList = [];
	let selectedVehicleId = null;
	let loading = true;
	let error = '';
	let showForm = false;

	onMount(async () => {
		try {
			vehicleList = await vehicles.list();
			if (vehicleList.length > 0) {
				selectedVehicleId = $currentVehicle?.id || vehicleList[0].id;
				await loadRecords();
			}
		} catch (err) {
			error = err.message;
		}
		loading = false;
	});

	async function loadRecords() {
		if (!selectedVehicleId) return;
		loading = true;
		try {
			records = await service.list(selectedVehicleId);
		} catch (err) {
			error = err.message;
		}
		loading = false;
	}

	async function handleCreate(event) {
		error = '';
		try {
			await service.create(selectedVehicleId, event.detail);
			showForm = false;
			await loadRecords();
		} catch (err) {
			error = err.message;
		}
	}

	async function handleDelete(recordId) {
		try {
			await service.delete(selectedVehicleId, recordId);
			await loadRecords();
		} catch (err) {
			error = err.message;
		}
	}

	function formatDate(d) {
		return new Date(d).toLocaleDateString();
	}
</script>

<div class="service-page">
	<div class="header">
		<h2>Service Records</h2>
		<div class="actions">
			{#if vehicleList.length > 1}
				<select bind:value={selectedVehicleId} on:change={loadRecords}>
					{#each vehicleList as v}
						<option value={v.id}>{v.nickname || v.vehicle_type} ({v.year || ''})</option>
					{/each}
				</select>
			{/if}
			<button class="primary" on:click={() => showForm = !showForm}>
				{showForm ? 'Cancel' : '+ Add Record'}
			</button>
		</div>
	</div>

	{#if error}
		<div class="error">{error}</div>
	{/if}

	{#if showForm && selectedVehicleId}
		<ServiceRecordForm vehicleId={selectedVehicleId} on:create={handleCreate} />
	{/if}

	{#if loading}
		<p class="loading">Loading...</p>
	{:else if vehicleList.length === 0}
		<div class="empty">
			<p>No vehicles registered. Add a vehicle from the Vehicle page first.</p>
		</div>
	{:else if records.length === 0}
		<div class="empty">
			<p>No service records yet. Start logging your maintenance.</p>
		</div>
	{:else}
		<div class="records">
			{#each records as record}
				<div class="record">
					<div class="record-header">
						<span class="record-type">{(record.service_type || 'service').replace(/_/g, ' ')}</span>
						<span class="record-date">{formatDate(record.service_date)}</span>
					</div>
					<div class="record-details">
						{#if record.mileage}
							<span class="detail">{record.mileage.toLocaleString()} mi</span>
						{/if}
						{#if record.cost}
							<span class="detail">${record.cost.toFixed(2)}</span>
						{/if}
						{#if record.performed_by}
							<span class="detail">by {record.performed_by}</span>
						{/if}
					</div>
					{#if record.description}
						<p class="record-desc">{record.description}</p>
					{/if}
					<button class="delete-btn" on:click={() => handleDelete(record.id)}>x</button>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.service-page {
		padding: 1rem;
	}
	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.actions {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}
	.actions select {
		width: auto;
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
	.records {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 1rem;
	}
	.record {
		position: relative;
		padding: 0.75rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
	}
	.record-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.3rem;
	}
	.record-type {
		font-weight: 600;
		color: var(--amber);
		text-transform: capitalize;
	}
	.record-date {
		color: var(--text-secondary);
		font-size: 0.8rem;
	}
	.record-details {
		display: flex;
		gap: 1rem;
		font-size: 0.8rem;
		color: var(--text-secondary);
	}
	.record-desc {
		margin-top: 0.35rem;
		font-size: 0.85rem;
		color: var(--text-primary);
	}
	.delete-btn {
		position: absolute;
		top: 0.5rem;
		right: 0.5rem;
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		font-size: 0.8rem;
		padding: 0.2rem 0.4rem;
	}
	.delete-btn:hover {
		color: var(--red);
	}
	.empty, .loading {
		text-align: center;
		padding: 3rem 1rem;
		color: var(--text-secondary);
	}
</style>

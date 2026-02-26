<script>
	import { onMount } from 'svelte';
	import { currentVehicle } from '$lib/stores.js';
	import { vehicles, service, kb } from '$lib/api.js';

	let vehicleList = [];
	let schedules = [];
	let kbStatus = null;
	let loading = true;
	let error = '';

	// New vehicle form
	let showAddForm = false;
	let newVehicle = { vehicle_type: 'fzj80', nickname: '', year: 1996, vin: '', current_mileage: null };

	onMount(async () => {
		await loadData();
	});

	async function loadData() {
		loading = true;
		try {
			vehicleList = await vehicles.list();
			if (vehicleList.length > 0 && !$currentVehicle) {
				currentVehicle.set(vehicleList[0]);
			}
			schedules = (await service.schedules('fzj80')).schedules || [];
			kbStatus = await kb.status();
		} catch (err) {
			error = err.message;
		}
		loading = false;
	}

	async function addVehicle() {
		try {
			const v = await vehicles.create(newVehicle);
			currentVehicle.set(v);
			showAddForm = false;
			newVehicle = { vehicle_type: 'fzj80', nickname: '', year: 1996, vin: '', current_mileage: null };
			await loadData();
		} catch (err) {
			error = err.message;
		}
	}

	async function selectVehicle(v) {
		currentVehicle.set(v);
	}
</script>

<div class="vehicle-page">
	<div class="header">
		<h2>Vehicle Info</h2>
		<button class="primary" on:click={() => showAddForm = !showAddForm}>
			{showAddForm ? 'Cancel' : '+ Add Vehicle'}
		</button>
	</div>

	{#if error}
		<div class="error">{error}</div>
	{/if}

	{#if showAddForm}
		<form class="add-form" on:submit|preventDefault={addVehicle}>
			<div class="row">
				<div class="field">
					<label>Nickname</label>
					<input bind:value={newVehicle.nickname} placeholder="e.g. Big Red" />
				</div>
				<div class="field">
					<label>Year</label>
					<input type="number" bind:value={newVehicle.year} min="1990" max="2000" />
				</div>
			</div>
			<div class="row">
				<div class="field">
					<label>VIN</label>
					<input bind:value={newVehicle.vin} placeholder="JT3DJ81W..." maxlength="17" />
				</div>
				<div class="field">
					<label>Mileage</label>
					<input type="number" bind:value={newVehicle.current_mileage} placeholder="mi" />
				</div>
			</div>
			<button type="submit" class="primary">Register Vehicle</button>
		</form>
	{/if}

	{#if loading}
		<p class="loading">Loading...</p>
	{:else}
		{#if vehicleList.length > 0}
			<div class="vehicles">
				{#each vehicleList as v}
					<div
						class="vehicle-card"
						class:active={$currentVehicle?.id === v.id}
						on:click={() => selectVehicle(v)}
						role="button"
						tabindex="0"
						on:keypress={(e) => e.key === 'Enter' && selectVehicle(v)}
					>
						<div class="vehicle-name">
							{v.nickname || 'FZJ80'}
							<span class="year">{v.year || ''}</span>
						</div>
						<div class="vehicle-meta">
							{#if v.current_mileage}
								<span>{v.current_mileage.toLocaleString()} mi</span>
							{/if}
							{#if v.vin}
								<span class="vin">{v.vin}</span>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="empty">
				<p>No vehicles registered. Add your Land Cruiser to get started.</p>
			</div>
		{/if}

		{#if schedules.length > 0}
			<div class="section">
				<h3>Maintenance Schedule</h3>
				<div class="schedule-list">
					{#each schedules as sched}
						<div class="schedule-item">
							<span class="sched-type">{sched.service_type.replace(/_/g, ' ')}</span>
							<span class="sched-desc">{sched.description}</span>
							{#if sched.interval_miles}
								<span class="sched-interval">every {sched.interval_miles.toLocaleString()} mi</span>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if kbStatus}
			<div class="section">
				<h3>Knowledge Base</h3>
				<div class="kb-stats">
					<span class="kb-total">{kbStatus.total_chunks} total chunks</span>
					<div class="kb-collections">
						{#each Object.entries(kbStatus.collections || {}) as [cat, count]}
							<span class="kb-cat">
								<span class="cat-name">{cat}</span>
								<span class="cat-count">{count}</span>
							</span>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.vehicle-page { padding: 1rem; }
	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
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
	.add-form {
		padding: 1rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		margin-bottom: 1rem;
	}
	.row { display: flex; gap: 0.75rem; margin-bottom: 0.5rem; }
	.field { flex: 1; }
	.field label { display: block; font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.2rem; }
	.vehicles { display: flex; flex-direction: column; gap: 0.5rem; }
	.vehicle-card {
		padding: 0.75rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		cursor: pointer;
		transition: all 0.15s;
	}
	.vehicle-card:hover { border-color: var(--border-active); }
	.vehicle-card.active { border-color: var(--green-dim); background: var(--green-bg); }
	.vehicle-name { font-weight: 600; }
	.year { color: var(--text-secondary); font-weight: 400; margin-left: 0.5rem; }
	.vehicle-meta { font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem; display: flex; gap: 1rem; }
	.vin { font-size: 0.75rem; color: var(--text-muted); }
	.section { margin-top: 1.5rem; }
	.section h3 { color: var(--amber); margin-bottom: 0.5rem; }
	.schedule-list { display: flex; flex-direction: column; gap: 0.3rem; }
	.schedule-item {
		display: flex;
		gap: 1rem;
		padding: 0.4rem 0.6rem;
		background: var(--bg-surface);
		border-radius: var(--radius);
		font-size: 0.85rem;
		align-items: center;
	}
	.sched-type { color: var(--green); font-weight: 600; min-width: 12ch; text-transform: capitalize; }
	.sched-desc { flex: 1; }
	.sched-interval { color: var(--amber); font-size: 0.8rem; }
	.kb-stats { padding: 0.5rem; }
	.kb-total { color: var(--green); font-weight: 600; }
	.kb-collections { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
	.kb-cat {
		font-size: 0.75rem;
		padding: 0.15rem 0.4rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--bg-surface);
	}
	.cat-name { color: var(--text-secondary); }
	.cat-count { color: var(--amber); margin-left: 0.3rem; }
	.empty, .loading { text-align: center; padding: 3rem 1rem; color: var(--text-secondary); }
</style>

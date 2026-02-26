<script>
	export let index = 0;
	export let source = '';
	export let category = '';
	export let score = 0;
	export let title = '';

	$: label = source.toUpperCase();
	$: scorePercent = Math.round(score * 100);
</script>

<span class="citation" title="{title || category} ({scorePercent}% match)">
	<span class="badge">[{index}]</span>
	<span class="source">{label}</span>
	{#if title}
		<span class="title">{title}</span>
	{/if}
</span>

<style>
	.citation {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		padding: 0.15rem 0.4rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--bg-surface);
		color: var(--text-secondary);
	}
	.badge {
		color: var(--amber);
		font-weight: 600;
	}
	.source {
		color: var(--green-dim);
		font-weight: 600;
	}
	.title {
		max-width: 15ch;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>

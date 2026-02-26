<script>
	import { marked } from 'marked';
	import SourceCitation from './SourceCitation.svelte';

	export let role = 'user';
	export let content = '';
	export let sources = [];
	export let streaming = false;

	$: rendered = role === 'assistant' ? marked.parse(content) : content;
</script>

<div class="message {role}" class:streaming>
	<div class="role-tag">{role === 'user' ? '>' : '<'}</div>
	<div class="content">
		{#if role === 'assistant'}
			{@html rendered}
		{:else}
			<p>{content}</p>
		{/if}
		{#if streaming}
			<span class="cursor">_</span>
		{/if}
		{#if sources.length > 0}
			<div class="sources">
				{#each sources as source}
					<SourceCitation {...source} />
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.message {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem 0;
		border-bottom: 1px solid var(--border);
	}
	.role-tag {
		color: var(--text-muted);
		font-weight: 700;
		min-width: 1rem;
		padding-top: 0.15rem;
	}
	.message.user .role-tag {
		color: var(--amber);
	}
	.message.assistant .role-tag {
		color: var(--green);
	}
	.content {
		flex: 1;
		overflow-wrap: break-word;
		min-width: 0;
	}
	.content :global(p) {
		margin-bottom: 0.5rem;
	}
	.content :global(ul), .content :global(ol) {
		margin: 0.25rem 0 0.5rem 1.25rem;
	}
	.content :global(code) {
		background: var(--bg-surface);
		padding: 0.1em 0.3em;
		border-radius: var(--radius);
		font-size: 0.9em;
	}
	.content :global(pre) {
		background: var(--bg-surface);
		padding: 0.75rem;
		border-radius: var(--radius);
		overflow-x: auto;
		margin: 0.5rem 0;
	}
	.cursor {
		color: var(--green);
		animation: blink 0.8s step-end infinite;
	}
	@keyframes blink {
		50% { opacity: 0; }
	}
	.sources {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-top: 0.5rem;
		padding-top: 0.5rem;
		border-top: 1px solid var(--border);
	}
	.streaming {
		opacity: 0.95;
	}
</style>

<script>
	import { createEventDispatcher } from 'svelte';
	import { isGenerating } from '$lib/stores.js';

	const dispatch = createEventDispatcher();

	let message = '';

	function handleSubmit() {
		const text = message.trim();
		if (!text || $isGenerating) return;
		dispatch('send', { message: text });
		message = '';
	}

	function handleKeydown(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}
</script>

<form class="chat-input" on:submit|preventDefault={handleSubmit}>
	<textarea
		bind:value={message}
		on:keydown={handleKeydown}
		placeholder={$isGenerating ? 'Generating...' : 'Ask about your FZJ80...'}
		disabled={$isGenerating}
		rows="1"
	></textarea>
	<button type="submit" class="primary" disabled={!message.trim() || $isGenerating}>
		{$isGenerating ? '...' : '>'}
	</button>
</form>

<style>
	.chat-input {
		display: flex;
		gap: 0.5rem;
		padding: 0.75rem;
		background: var(--bg-secondary);
		border-top: 1px solid var(--border);
	}
	textarea {
		flex: 1;
		resize: none;
		min-height: 2.4rem;
		max-height: 8rem;
		font-family: var(--font-mono);
	}
	button {
		align-self: flex-end;
		min-width: 3rem;
		font-weight: 700;
	}
</style>

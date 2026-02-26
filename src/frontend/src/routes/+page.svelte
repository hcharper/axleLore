<script>
	import { onMount } from 'svelte';
	import { chatMessages, isGenerating, currentVehicle } from '$lib/stores.js';
	import { streamChat } from '$lib/sse.js';
	import ChatMessage from '../components/ChatMessage.svelte';
	import ChatInput from '../components/ChatInput.svelte';

	let chatContainer;

	onMount(() => {
		if ($chatMessages.length === 0) {
			chatMessages.set([{
				role: 'assistant',
				content: 'AxleLore online. Ask me anything about your FZJ80 Land Cruiser.',
				sources: []
			}]);
		}
	});

	function scrollToBottom() {
		if (chatContainer) {
			setTimeout(() => {
				chatContainer.scrollTop = chatContainer.scrollHeight;
			}, 10);
		}
	}

	async function handleSend(event) {
		const { message } = event.detail;
		const vehicleId = $currentVehicle?.id || null;

		// Add user message
		chatMessages.update(msgs => [...msgs, { role: 'user', content: message, sources: [] }]);
		scrollToBottom();

		// Add placeholder for assistant
		chatMessages.update(msgs => [...msgs, {
			role: 'assistant',
			content: '',
			sources: [],
			streaming: true
		}]);

		isGenerating.set(true);
		scrollToBottom();

		try {
			for await (const event of streamChat(message, vehicleId)) {
				if (event.type === 'token') {
					chatMessages.update(msgs => {
						const last = msgs[msgs.length - 1];
						last.content += event.token;
						return [...msgs];
					});
					scrollToBottom();
				} else if (event.type === 'sources') {
					chatMessages.update(msgs => {
						const last = msgs[msgs.length - 1];
						last.sources = event.sources;
						return [...msgs];
					});
				} else if (event.type === 'done') {
					chatMessages.update(msgs => {
						const last = msgs[msgs.length - 1];
						last.streaming = false;
						return [...msgs];
					});
				} else if (event.type === 'error') {
					chatMessages.update(msgs => {
						const last = msgs[msgs.length - 1];
						last.content = `Error: ${event.error}`;
						last.streaming = false;
						return [...msgs];
					});
				}
			}
		} catch (err) {
			chatMessages.update(msgs => {
				const last = msgs[msgs.length - 1];
				last.content = `Connection error: ${err.message}`;
				last.streaming = false;
				return [...msgs];
			});
		}

		isGenerating.set(false);
	}
</script>

<div class="chat-page">
	<div class="chat-messages" bind:this={chatContainer}>
		{#each $chatMessages as msg}
			<ChatMessage
				role={msg.role}
				content={msg.content}
				sources={msg.sources || []}
				streaming={msg.streaming || false}
			/>
		{/each}
	</div>
	<ChatInput on:send={handleSend} />
</div>

<style>
	.chat-page {
		flex: 1;
		display: flex;
		flex-direction: column;
		max-height: calc(100vh - 3rem);
	}
	.chat-messages {
		flex: 1;
		overflow-y: auto;
		padding: 0.75rem 1rem;
	}
</style>

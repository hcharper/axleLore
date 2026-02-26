<script>
	export let label = '';
	export let value = null;
	export let unit = '';
	export let min = 0;
	export let max = 100;
	export let warnAt = null;
	export let critAt = null;

	$: displayValue = value !== null && value !== undefined ? value : '--';
	$: pct = value !== null ? Math.min(1, Math.max(0, (value - min) / (max - min))) : 0;
	$: angle = -135 + pct * 270;

	// SVG arc for the gauge background and fill
	$: arcLength = 270;
	$: dashArray = `${pct * arcLength} ${arcLength}`;

	$: color = getColor(value);

	function getColor(v) {
		if (v === null || v === undefined) return 'var(--text-muted)';
		if (critAt !== null && v >= critAt) return 'var(--red)';
		if (warnAt !== null && v >= warnAt) return 'var(--amber)';
		return 'var(--green)';
	}
</script>

<div class="gauge">
	<svg viewBox="0 0 100 100">
		<!-- Background arc -->
		<circle
			cx="50" cy="50" r="40"
			fill="none"
			stroke="var(--border)"
			stroke-width="6"
			stroke-dasharray="270 360"
			stroke-dashoffset="-135"
			stroke-linecap="round"
			transform="rotate(0, 50, 50)"
			class="arc-bg"
		/>
		<!-- Value arc -->
		<circle
			cx="50" cy="50" r="40"
			fill="none"
			stroke={color}
			stroke-width="6"
			stroke-dasharray={dashArray}
			stroke-dashoffset="-135"
			stroke-linecap="round"
			class="arc-fill"
		/>
	</svg>
	<div class="reading" style="color: {color}">
		<span class="value">{displayValue}</span>
		<span class="unit">{unit}</span>
	</div>
	<div class="label">{label}</div>
</div>

<style>
	.gauge {
		position: relative;
		width: 120px;
		text-align: center;
	}
	svg {
		width: 100%;
		height: auto;
		transform: rotate(135deg);
	}
	.arc-bg, .arc-fill {
		fill: none;
		transition: stroke-dasharray 0.3s ease;
	}
	.reading {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -60%);
		text-align: center;
	}
	.value {
		font-size: 1.3rem;
		font-weight: 700;
		display: block;
		line-height: 1;
	}
	.unit {
		font-size: 0.6rem;
		color: var(--text-secondary);
	}
	.label {
		font-size: 0.7rem;
		color: var(--text-secondary);
		margin-top: -0.5rem;
	}
</style>

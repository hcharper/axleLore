import { useState, useEffect, useCallback } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView } from 'react-native';
import { obd2 } from '../../lib/api';
import { createOBD2Socket, SensorData } from '../../lib/ws';

const THEME = {
  bg: '#0a0e14',
  surface: '#141920',
  border: '#1e2530',
  green: '#33ff33',
  amber: '#ffb833',
  red: '#ff4444',
  text: '#c5cdd8',
  muted: '#6b7a8d',
};

function GaugeCard({
  label,
  value,
  unit,
  warn,
  crit,
}: {
  label: string;
  value: number | null;
  unit: string;
  warn?: number;
  crit?: number;
}) {
  const display = value !== null && value !== undefined ? String(value) : '--';
  let color = THEME.green;
  if (value !== null && crit && value >= crit) color = THEME.red;
  else if (value !== null && warn && value >= warn) color = THEME.amber;

  return (
    <View style={styles.gauge}>
      <Text style={[styles.gaugeValue, { color }]}>{display}</Text>
      <Text style={styles.gaugeUnit}>{unit}</Text>
      <Text style={styles.gaugeLabel}>{label}</Text>
    </View>
  );
}

export default function DashboardScreen() {
  const [sensorData, setSensorData] = useState<SensorData | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const [ws, setWs] = useState<ReturnType<typeof createOBD2Socket> | null>(null);

  const connect = useCallback(() => {
    setError('');
    const socket = createOBD2Socket(
      (data) => {
        setSensorData(data);
        setConnected(true);
      },
      (err) => setError(err),
    );
    setWs(socket);
  }, []);

  const disconnect = useCallback(() => {
    ws?.close();
    setWs(null);
    setSensorData(null);
    setConnected(false);
  }, [ws]);

  useEffect(() => {
    return () => {
      ws?.close();
    };
  }, [ws]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>OBD-II Dashboard</Text>
        {connected ? (
          <Pressable style={styles.btn} onPress={disconnect}>
            <Text style={styles.btnText}>Disconnect</Text>
          </Pressable>
        ) : (
          <Pressable style={[styles.btn, styles.btnPrimary]} onPress={connect}>
            <Text style={[styles.btnText, { color: THEME.green }]}>Connect</Text>
          </Pressable>
        )}
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <View style={styles.gaugeGrid}>
        <GaugeCard label="RPM" value={sensorData?.rpm ?? null} unit="rpm" warn={4500} crit={5500} />
        <GaugeCard label="Speed" value={sensorData?.speed_mph ?? null} unit="mph" />
        <GaugeCard
          label="Coolant"
          value={sensorData?.coolant_temp_f ?? null}
          unit="°F"
          warn={220}
          crit={240}
        />
        <GaugeCard label="Throttle" value={sensorData?.throttle_pct ?? null} unit="%" />
        <GaugeCard
          label="Load"
          value={sensorData?.engine_load_pct ?? null}
          unit="%"
          warn={85}
          crit={95}
        />
        <GaugeCard label="Intake" value={sensorData?.intake_temp_f ?? null} unit="°F" warn={150} />
      </View>

      {!sensorData && !error && (
        <Text style={styles.hint}>Connect to OBD-II to see live engine data.</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: THEME.bg },
  content: { padding: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  title: { color: THEME.text, fontFamily: 'monospace', fontWeight: '700', fontSize: 16 },
  btn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: THEME.border,
    backgroundColor: THEME.surface,
  },
  btnPrimary: { borderColor: '#1a8c1a', backgroundColor: 'rgba(51,255,51,0.08)' },
  btnText: { color: THEME.text, fontFamily: 'monospace', fontSize: 12 },
  error: {
    color: THEME.red,
    backgroundColor: 'rgba(255,68,68,0.08)',
    padding: 8,
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 12,
  },
  gaugeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    justifyContent: 'center',
  },
  gauge: {
    width: 100,
    backgroundColor: THEME.surface,
    borderColor: THEME.border,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  gaugeValue: { fontSize: 22, fontWeight: '700', fontFamily: 'monospace' },
  gaugeUnit: { fontSize: 10, color: THEME.muted, fontFamily: 'monospace' },
  gaugeLabel: { fontSize: 11, color: THEME.muted, fontFamily: 'monospace', marginTop: 4 },
  hint: { color: THEME.muted, fontFamily: 'monospace', fontSize: 12, textAlign: 'center', marginTop: 40 },
});

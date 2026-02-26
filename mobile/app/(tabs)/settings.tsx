import { useState, useEffect } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, ScrollView } from 'react-native';
import { system, checkHealth, getBaseUrl, setBaseUrl, loadBaseUrl } from '../../lib/api';
import { discoverDevices, DiscoveredDevice } from '../../lib/discovery';

const THEME = {
  bg: '#0a0e14',
  surface: '#141920',
  border: '#1e2530',
  green: '#33ff33',
  greenDim: '#1a8c1a',
  amber: '#ffb833',
  red: '#ff4444',
  text: '#c5cdd8',
  muted: '#6b7a8d',
};

export default function SettingsScreen() {
  const [baseUrl, setBaseUrlState] = useState('');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [versionInfo, setVersionInfo] = useState<any>(null);
  const [deviceInfo, setDeviceInfo] = useState<any>(null);
  const [devices, setDevices] = useState<DiscoveredDevice[]>([]);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    init();
  }, []);

  async function init() {
    const url = await loadBaseUrl();
    setBaseUrlState(url);
    await testConnection();
  }

  async function testConnection() {
    setError('');
    const ok = await checkHealth();
    setConnected(ok);
    if (ok) {
      try {
        const [ver, dev] = await Promise.all([system.version(), system.device()]);
        setVersionInfo(ver);
        setDeviceInfo(dev);
      } catch (err: any) {
        setError(err.message);
      }
    }
  }

  async function saveUrl() {
    await setBaseUrl(baseUrl);
    await testConnection();
  }

  async function scan() {
    setScanning(true);
    try {
      const found = await discoverDevices(5000);
      setDevices(found);
    } catch {
      setError('mDNS scan failed');
    }
    setScanning(false);
  }

  async function selectDevice(device: DiscoveredDevice) {
    const url = `http://${device.address}:${device.port}`;
    setBaseUrlState(url);
    await setBaseUrl(url);
    await testConnection();
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Settings</Text>

      {/* Connection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connection</Text>
        <View style={styles.row}>
          <View style={[styles.dot, connected === true && styles.dotGreen, connected === false && styles.dotRed]} />
          <Text style={styles.label}>
            {connected === null ? 'Checking...' : connected ? 'Connected' : 'Disconnected'}
          </Text>
        </View>
        <TextInput
          style={styles.input}
          value={baseUrl}
          onChangeText={setBaseUrlState}
          placeholder="http://axlelore.local:8000"
          placeholderTextColor={THEME.muted}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <View style={styles.btnRow}>
          <Pressable style={[styles.btn, styles.btnPrimary]} onPress={saveUrl}>
            <Text style={[styles.btnText, { color: THEME.green }]}>Connect</Text>
          </Pressable>
          <Pressable style={styles.btn} onPress={scan}>
            <Text style={styles.btnText}>{scanning ? 'Scanning...' : 'Discover'}</Text>
          </Pressable>
        </View>

        {devices.length > 0 && (
          <View style={styles.deviceList}>
            {devices.map((d, i) => (
              <Pressable key={i} style={styles.deviceItem} onPress={() => selectDevice(d)}>
                <Text style={styles.deviceName}>{d.name}</Text>
                <Text style={styles.deviceAddr}>{d.address}:{d.port}</Text>
              </Pressable>
            ))}
          </View>
        )}
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {/* Version info */}
      {versionInfo && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Version</Text>
          <InfoRow label="Software" value={versionInfo.software_version} />
          <InfoRow label="KB Pack" value={versionInfo.kb_version} />
          <InfoRow label="Model" value={versionInfo.model} />
          <InfoRow label="Fallback" value={versionInfo.fallback_model} />
        </View>
      )}

      {/* Device info */}
      {deviceInfo && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Device</Text>
          <InfoRow label="ID" value={deviceInfo.device_id} />
          <InfoRow label="Hostname" value={deviceInfo.hostname} />
          <InfoRow label="Hardware" value={deviceInfo.hardware} />
        </View>
      )}
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: THEME.bg },
  content: { padding: 16 },
  title: { color: THEME.text, fontFamily: 'monospace', fontWeight: '700', fontSize: 16, marginBottom: 12 },
  section: {
    backgroundColor: THEME.surface,
    borderColor: THEME.border,
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  sectionTitle: { color: THEME.amber, fontFamily: 'monospace', fontWeight: '600', fontSize: 13, marginBottom: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: THEME.muted },
  dotGreen: { backgroundColor: THEME.green },
  dotRed: { backgroundColor: THEME.red },
  label: { color: THEME.text, fontFamily: 'monospace', fontSize: 12 },
  input: {
    backgroundColor: THEME.bg,
    color: THEME.text,
    fontFamily: 'monospace',
    fontSize: 12,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: THEME.border,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 8,
  },
  btnRow: { flexDirection: 'row', gap: 8 },
  btn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: THEME.border,
    backgroundColor: THEME.surface,
    alignItems: 'center',
  },
  btnPrimary: { borderColor: THEME.greenDim, backgroundColor: 'rgba(51,255,51,0.08)' },
  btnText: { color: THEME.text, fontFamily: 'monospace', fontSize: 12 },
  deviceList: { marginTop: 8, gap: 4 },
  deviceItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 8,
    backgroundColor: THEME.bg,
    borderRadius: 4,
  },
  deviceName: { color: THEME.green, fontFamily: 'monospace', fontSize: 12 },
  deviceAddr: { color: THEME.muted, fontFamily: 'monospace', fontSize: 11 },
  error: {
    color: THEME.red,
    backgroundColor: 'rgba(255,68,68,0.08)',
    padding: 8,
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 12,
  },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 3 },
  infoLabel: { color: THEME.muted, fontFamily: 'monospace', fontSize: 12 },
  infoValue: { color: THEME.text, fontFamily: 'monospace', fontSize: 12 },
});

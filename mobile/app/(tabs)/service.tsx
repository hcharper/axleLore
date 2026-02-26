import { useState, useEffect, useCallback } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet, ScrollView } from 'react-native';
import { service, vehicles } from '../../lib/api';

const THEME = {
  bg: '#0a0e14',
  surface: '#141920',
  border: '#1e2530',
  green: '#33ff33',
  amber: '#ffb833',
  text: '#c5cdd8',
  muted: '#6b7a8d',
};

interface ServiceRecord {
  id: number;
  service_date: string;
  service_type: string;
  mileage?: number;
  description?: string;
  cost?: number;
  performed_by?: string;
}

export default function ServiceScreen() {
  const [records, setRecords] = useState<ServiceRecord[]>([]);
  const [vehicleList, setVehicleList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const vList = await vehicles.list();
      setVehicleList(vList);
      if (vList.length > 0) {
        const recs = await service.list(vList[0].id);
        setRecords(recs);
      }
    } catch (err: any) {
      setError(err.message);
    }
    setLoading(false);
  }

  const renderRecord = ({ item }: { item: ServiceRecord }) => (
    <View style={styles.record}>
      <View style={styles.recordHeader}>
        <Text style={styles.recordType}>{(item.service_type || 'service').replace(/_/g, ' ')}</Text>
        <Text style={styles.recordDate}>{new Date(item.service_date).toLocaleDateString()}</Text>
      </View>
      <View style={styles.recordDetails}>
        {item.mileage ? (
          <Text style={styles.detail}>{item.mileage.toLocaleString()} mi</Text>
        ) : null}
        {item.cost ? <Text style={styles.detail}>${item.cost.toFixed(2)}</Text> : null}
        {item.performed_by ? <Text style={styles.detail}>by {item.performed_by}</Text> : null}
      </View>
      {item.description ? <Text style={styles.recordDesc}>{item.description}</Text> : null}
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Service Records</Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {loading ? (
        <Text style={styles.hint}>Loading...</Text>
      ) : records.length === 0 ? (
        <Text style={styles.hint}>No service records yet.</Text>
      ) : (
        <FlatList
          data={records}
          renderItem={renderRecord}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: THEME.bg, padding: 16 },
  title: { color: THEME.text, fontFamily: 'monospace', fontWeight: '700', fontSize: 16, marginBottom: 12 },
  error: {
    color: '#ff4444',
    backgroundColor: 'rgba(255,68,68,0.08)',
    padding: 8,
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 12,
  },
  list: { gap: 8 },
  record: {
    backgroundColor: THEME.surface,
    borderColor: THEME.border,
    borderWidth: 1,
    borderRadius: 4,
    padding: 12,
  },
  recordHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  recordType: { color: THEME.amber, fontWeight: '600', fontFamily: 'monospace', fontSize: 13, textTransform: 'capitalize' },
  recordDate: { color: THEME.muted, fontFamily: 'monospace', fontSize: 11 },
  recordDetails: { flexDirection: 'row', gap: 12 },
  detail: { color: THEME.muted, fontFamily: 'monospace', fontSize: 11 },
  recordDesc: { color: THEME.text, fontFamily: 'monospace', fontSize: 12, marginTop: 4 },
  hint: { color: THEME.muted, fontFamily: 'monospace', fontSize: 12, textAlign: 'center', marginTop: 40 },
});

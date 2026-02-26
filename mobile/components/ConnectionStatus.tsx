import { View, Text, StyleSheet } from 'react-native';

interface Props {
  connected: boolean;
  host?: string;
}

export default function ConnectionStatus({ connected, host }: Props) {
  return (
    <View style={styles.container}>
      <View style={[styles.dot, connected ? styles.dotGreen : styles.dotRed]} />
      <Text style={styles.text}>
        {connected ? `Connected to ${host || 'AxleLore'}` : 'Disconnected'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  dotGreen: { backgroundColor: '#33ff33' },
  dotRed: { backgroundColor: '#ff4444' },
  text: {
    color: '#6b7a8d',
    fontFamily: 'monospace',
    fontSize: 10,
  },
});

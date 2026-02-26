import { useEffect } from 'react';
import { Tabs } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { loadBaseUrl } from '../lib/api';

const THEME = {
  bg: '#0a0e14',
  surface: '#141920',
  border: '#1e2530',
  green: '#33ff33',
  amber: '#ffb833',
  text: '#c5cdd8',
  muted: '#6b7a8d',
};

export default function Layout() {
  useEffect(() => {
    loadBaseUrl();
  }, []);

  return (
    <>
      <StatusBar style="light" backgroundColor={THEME.bg} />
      <Tabs
        screenOptions={{
          headerStyle: { backgroundColor: THEME.surface },
          headerTintColor: THEME.green,
          headerTitleStyle: { fontFamily: 'monospace', fontWeight: '700' },
          tabBarStyle: {
            backgroundColor: THEME.surface,
            borderTopColor: THEME.border,
          },
          tabBarActiveTintColor: THEME.green,
          tabBarInactiveTintColor: THEME.muted,
          tabBarLabelStyle: { fontFamily: 'monospace', fontSize: 10 },
        }}
      >
        <Tabs.Screen
          name="(tabs)/chat"
          options={{
            title: 'Chat',
            headerTitle: 'AxleLore',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="chatbubble-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="(tabs)/dashboard"
          options={{
            title: 'Dashboard',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="speedometer-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="(tabs)/service"
          options={{
            title: 'Service',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="construct-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="(tabs)/settings"
          options={{
            title: 'Settings',
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="settings-outline" size={size} color={color} />
            ),
          }}
        />
      </Tabs>
    </>
  );
}

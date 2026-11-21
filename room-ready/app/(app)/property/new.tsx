import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { useCreateProperty } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function NewPropertyScreen() {
  useHideTabHeader();
  const guard = useRoleGuard(ROUTE_ROLES.propertyNew);
  if (guard) return guard;

  const create = useCreateProperty();
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [postcode, setPostcode] = useState('');
  const [maxOccupants, setMaxOccupants] = useState('');
  const [licenceHeld, setLicenceHeld] = useState(false);
  const [licenceNumber, setLicenceNumber] = useState('');
  const [description, setDescription] = useState('');
  const [emergencyContact, setEmergencyContact] = useState('');
  const [houseRules, setHouseRules] = useState('');

  async function handleSubmit() {
    if (!address.trim() || !city.trim() || !postcode.trim()) {
      Alert.alert('Missing fields', 'Address, city and postcode are required');
      return;
    }
    try {
      const result = await create.mutateAsync({
        name: address.trim(),
        addressLine1: address.trim(),
        city: city.trim(),
        postcode: postcode.trim().toUpperCase(),
        hmoLicenceNumber: licenceHeld && licenceNumber.trim() ? licenceNumber.trim() : undefined,
        maxOccupants: parseInt(maxOccupants, 10) || 0,
        description: description.trim() || undefined,
        emergencyContact: emergencyContact.trim() || undefined,
        houseRules: houseRules.trim() || undefined,
      }) as { property: { id: string } };
      const newId = result.property.id;
      Alert.alert('Property created', 'Add rooms when you are ready.', [
        { text: 'Done', onPress: () => router.replace(`/(app)/property/${newId}`) },
        {
          text: 'Add room',
          onPress: () => router.replace({ pathname: '/(app)/property/add-room', params: { propertyId: newId } }),
        },
      ]);
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Failed to create property');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <Text style={styles.title}>Add property</Text>

      <Input label="Address" value={address} onChangeText={setAddress} placeholder="Street and number" />
      <Input label="Postcode" value={postcode} onChangeText={setPostcode} placeholder="Postcode" autoCapitalize="characters" />
      <Input label="City" value={city} onChangeText={setCity} placeholder="City" />
      <Input label="Licence max occupants" value={maxOccupants} onChangeText={setMaxOccupants} keyboardType="number-pad" placeholder="0" />

      <View style={styles.toggleRow}>
        <Text style={styles.toggleLabel}>HMO licence held</Text>
        <Switch
          value={licenceHeld}
          onValueChange={setLicenceHeld}
          trackColor={{ true: theme.colors.secondary, false: theme.colors.border }}
          accessibilityLabel="HMO licence held"
        />
      </View>
      {licenceHeld ? (
        <Input label="Licence number" value={licenceNumber} onChangeText={setLicenceNumber} placeholder="Licence number" />
      ) : null}

      <Input label="Description" value={description} onChangeText={setDescription} multiline numberOfLines={3} placeholder="Optional" />
      <Input label="Emergency contact" value={emergencyContact} onChangeText={setEmergencyContact} placeholder="Name and phone" />
      <Input label="House rules" value={houseRules} onChangeText={setHouseRules} multiline numberOfLines={3} placeholder="Optional" />

      <Button title="Create property" onPress={handleSubmit} loading={create.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  title: { fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.lg },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.md,
    minHeight: 44,
  },
  toggleLabel: { fontFamily: FONT_MEDIUM, fontSize: 15, color: theme.colors.text },
});

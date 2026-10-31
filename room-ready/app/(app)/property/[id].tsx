import { router, useLocalSearchParams } from 'expo-router';
import { Image, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { ComplianceChecklist } from '@/components/compliance/ComplianceChecklist';
import { ComplianceScoreCard } from '@/components/compliance/ComplianceScoreCard';
import { CouncilContactCard, CouncilStandardsBanner } from '@/components/compliance/CouncilStandardsBanner';
import { PropertyActionBar } from '@/components/property/PropertyActionBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { SectionHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { HMO_ROOM_STANDARDS, isBirminghamPostcode } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatGBP, formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useProperty } from '@/hooks/useApi';
import { assessPropertyCompliance, assessRoomCompliance } from '@/lib/compliance';
import { openDocumentFile } from '@/lib/openDocument';
import { propertyCoverUrl } from '@/lib/propertyCovers';

export default function PropertyDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useProperty(id);

  if (isLoading) return <LoadingScreen message="Loading property..." />;
  if (error || !data) return <ErrorState message="Property not found" onRetry={refetch} />;

  const property = data.property;
  const occupied = property.rooms?.filter((r) => r.status === 'occupied').length ?? 0;
  const totalRooms = property.rooms?.length ?? 0;
  const voids = totalRooms - occupied;
  const compliance = assessPropertyCompliance(property);
  const isBirmingham = isBirminghamPostcode(property.postcode);
  const canManage = ['landlord', 'property_manager', 'admin'].includes(user?.role ?? '');
  const listableRoom = property.rooms?.find((r) => r.status === 'available' && !r.listing);
  const openRepairs = property._count?.maintenance ?? 0;
  const cover = propertyCoverUrl(property.id);
  const docs = property.documents ?? [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
    >
      {isBirmingham && <CouncilStandardsBanner variant="compact" />}

      <Card style={styles.hero} padded={false}>
        <Image source={{ uri: cover }} style={styles.cover} resizeMode="cover" />
        <View style={styles.heroBody}>
          <Text style={styles.title}>{property.name}</Text>
          <Text style={styles.address}>
            {property.addressLine1}
            {property.addressLine2 ? `, ${property.addressLine2}` : ''}
            {'\n'}
            {property.city}, {property.postcode}
          </Text>
          <View style={styles.heroBadges}>
            {property.hmoLicenceNumber ? <Badge label="HMO licensed" variant="info" format={false} /> : null}
            <Badge
              label={`${compliance.score}% checks`}
              variant={compliance.score >= 85 ? 'success' : compliance.score >= 60 ? 'warning' : 'error'}
              format={false}
            />
          </View>
        </View>
      </Card>

      <View style={styles.stats}>
        <View style={styles.stat}>
          <Text style={styles.statVal}>{totalRooms}</Text>
          <Text style={styles.statLbl}>Rooms</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statVal}>{occupied}</Text>
          <Text style={styles.statLbl}>Occupied</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statVal}>{voids}</Text>
          <Text style={styles.statLbl}>Voids</Text>
        </View>
        <View style={styles.stat}>
          <Text style={styles.statVal}>{property.maxOccupants}</Text>
          <Text style={styles.statLbl}>Licence max</Text>
        </View>
      </View>

      {canManage && <PropertyActionBar propertyId={id} listableRoomId={listableRoom?.id} />}

      <View style={styles.quickLinks}>
        <Button
          title={openRepairs > 0 ? `Repairs (${openRepairs})` : 'Repairs'}
          variant="outline"
          size="sm"
          onPress={() => router.push('/(app)/(tabs)/maintenance')}
          style={styles.quickBtn}
        />
        <Button
          title="Documents"
          variant="outline"
          size="sm"
          onPress={() => router.push('/(app)/documents')}
          style={styles.quickBtn}
        />
        <Button
          title="Listings"
          variant="outline"
          size="sm"
          onPress={() => router.push('/(app)/(tabs)/listings')}
          style={styles.quickBtn}
        />
      </View>

      <ComplianceScoreCard report={compliance} />

      {property.hmoLicenceNumber && (
        <Card style={styles.licenceCard}>
          <View style={styles.licenceHeader}>
            <Text style={styles.licenceTitle}>HMO licence</Text>
            <Badge label="Registered" variant="info" format={false} />
          </View>
          <Text style={styles.licenceRef}>{property.hmoLicenceNumber}</Text>
          <Text style={styles.licenceNote}>Display at the property entrance · Housing Act 2004</Text>
        </Card>
      )}

      <ComplianceChecklist checks={compliance.checks} />

      {compliance.roomIssues.length > 0 && (
        <Card style={styles.issueCard}>
          <Text style={styles.issueTitle}>Room size issues</Text>
          {compliance.roomIssues.map((issue) => (
            <Text key={issue.roomId} style={styles.issueText}>
              • {issue.roomName}: {issue.issue}
            </Text>
          ))}
        </Card>
      )}

      <Text style={styles.standardsNote}>
        Minimum standards: {HMO_ROOM_STANDARDS.singleOccupancy}m² single · {HMO_ROOM_STANDARDS.doubleOccupancy}m² double
      </Text>

      {property.emergencyContact && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Responsible person</Text>
          <Text style={styles.body}>{property.emergencyContact}</Text>
        </Card>
      )}

      {property.houseRules && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>House rules & waste</Text>
          <Text style={styles.body}>{property.houseRules}</Text>
        </Card>
      )}

      <SectionHeader title="Rooms" />
      {property.rooms?.length ? (
        property.rooms.map((room) => {
          const roomIssue = assessRoomCompliance(room);
          return (
            <Card key={room.id} style={roomIssue ? [styles.roomCard, styles.roomCardIssue] : styles.roomCard}>
              <View style={styles.roomHeader}>
                <Text style={styles.roomName}>{room.name}</Text>
                <Badge
                  label={room.status}
                  variant={room.status === 'available' ? 'success' : room.status === 'occupied' ? 'info' : 'default'}
                />
              </View>
              <Text style={styles.roomMeta}>
                Rent {formatGBP(room.rentPcm)}/pcm · Deposit {formatGBP(room.deposit)}
                {room.sizeSqm ? ` · ${room.sizeSqm}m²` : ''}
                {room.ensuite ? ' · Ensuite' : ''}
              </Text>
              {roomIssue && <Text style={styles.roomWarning}>{roomIssue}</Text>}
              {room.tenancies?.[0]?.tenant && (
                <View style={styles.tenantRow}>
                  <Ionicons name="person-outline" size={14} color={theme.colors.secondary} />
                  <Text style={styles.tenant}>
                    {room.tenancies[0].tenant.firstName} {room.tenancies[0].tenant.lastName}
                  </Text>
                </View>
              )}
              {room.listing?.status === 'active' && (
                <Button
                  title="View listing"
                  variant="outline"
                  size="sm"
                  onPress={() => router.push(`/(app)/listing/${room.listing!.id}`)}
                  style={styles.roomBtn}
                />
              )}
              {canManage && room.status === 'available' && !room.listing && (
                <Button
                  title="Create listing"
                  variant="secondary"
                  size="sm"
                  onPress={() =>
                    router.push({ pathname: '/(app)/listing/new', params: { roomId: room.id, propertyId: id } })
                  }
                  style={styles.roomBtn}
                />
              )}
            </Card>
          );
        })
      ) : canManage ? (
        <EmptyState
          title="No rooms yet"
          message="Add rooms to track occupancy, rent, and create listings for vacancies."
          icon="bed-outline"
          actionLabel="Add first room"
          onAction={() => router.push({ pathname: '/(app)/property/add-room', params: { propertyId: id } })}
        />
      ) : (
        <Card style={styles.missingDocs}>
          <Text style={styles.missingBody}>No room information available for this property.</Text>
        </Card>
      )}

      <SectionHeader
        title="Documents"
        action={
          canManage ? (
            <Text
              style={styles.addLink}
              onPress={() =>
                router.push({ pathname: '/(app)/property/upload-document', params: { propertyId: id } })
              }
            >
              + Upload
            </Text>
          ) : undefined
        }
      />
      {docs.length ? (
        docs.map((doc) => {
          const expired = !!(doc.expiryDate && new Date(doc.expiryDate) < new Date());
          return (
            <Pressable key={doc.id} onPress={() => openDocumentFile(doc.fileUrl)}>
              <Card style={expired ? [styles.docCard, styles.docExpired] : styles.docCard}>
                <View style={styles.docTop}>
                  <View style={styles.docIcon}>
                    <Ionicons name="document-text-outline" size={18} color={theme.colors.secondary} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.docName}>{doc.name}</Text>
                    <Text style={styles.docType}>{doc.type.replace(/_/g, ' ')}</Text>
                    {doc.expiryDate && (
                      <Text style={[styles.docExpiry, expired && styles.docExpiryBad]}>
                        {expired ? 'Expired' : 'Expires'} {formatUKDate(doc.expiryDate)}
                      </Text>
                    )}
                  </View>
                  <Badge label={expired ? 'Expired' : 'Read'} variant={expired ? 'error' : 'success'} format={false} />
                </View>
              </Card>
            </Pressable>
          );
        })
      ) : (
        <Card style={styles.missingDocs}>
          <Text style={styles.missingTitle}>Documents required</Text>
          <Text style={styles.missingBody}>
            Upload HMO licence, CP12, EICR, EPC and fire risk assessment to achieve full compliance.
          </Text>
        </Card>
      )}

      <CouncilContactCard />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  hero: { marginBottom: theme.spacing.md, overflow: 'hidden' },
  cover: { width: '100%', height: 168, backgroundColor: theme.colors.surfaceMuted },
  heroBody: { padding: theme.spacing.md },
  title: {
    fontSize: 22,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.4,
  },
  address: {
    color: theme.colors.textSecondary,
    marginTop: 8,
    lineHeight: 20,
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
  },
  heroBadges: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 12 },
  stats: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: theme.spacing.md,
  },
  stat: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  statVal: {
    fontSize: 18,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
  },
  statLbl: {
    fontSize: 11,
    color: theme.colors.textMuted,
    marginTop: 2,
    fontFamily: FONT_MEDIUM,
  },
  quickLinks: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: theme.spacing.md,
  },
  quickBtn: { flex: 1 },
  licenceCard: {
    backgroundColor: theme.colors.accentLight,
    borderColor: theme.colors.border,
    marginBottom: theme.spacing.md,
    marginTop: theme.spacing.md,
  },
  licenceHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  licenceTitle: { fontFamily: FONT_SEMIBOLD, fontWeight: '700', fontSize: 15, color: theme.colors.text },
  licenceRef: {
    fontSize: 18,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.secondary,
    marginTop: 8,
    letterSpacing: 0.3,
  },
  licenceNote: { fontSize: 12, color: theme.colors.textSecondary, marginTop: 6, fontFamily: FONT_MEDIUM },
  issueCard: {
    backgroundColor: theme.colors.errorLight,
    borderColor: theme.colors.error,
    marginTop: theme.spacing.md,
  },
  issueTitle: { fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.error, marginBottom: 8 },
  issueText: { fontSize: 13, color: theme.colors.textSecondary, marginBottom: 4, fontFamily: FONT_MEDIUM },
  standardsNote: {
    fontSize: 12,
    color: theme.colors.textMuted,
    textAlign: 'center',
    marginVertical: theme.spacing.md,
    fontFamily: FONT_MEDIUM,
  },
  section: { marginBottom: theme.spacing.md },
  sectionTitle: { fontFamily: FONT_SEMIBOLD, fontWeight: '700', color: theme.colors.text, marginBottom: 6 },
  body: { color: theme.colors.textSecondary, lineHeight: 22, fontFamily: FONT_MEDIUM },
  addLink: { color: theme.colors.secondary, fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 14 },
  roomCard: { marginBottom: theme.spacing.sm },
  roomCardIssue: { borderColor: theme.colors.warning, backgroundColor: theme.colors.warningLight },
  roomHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  roomName: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 16, color: theme.colors.text, flex: 1 },
  roomMeta: { color: theme.colors.textSecondary, marginTop: 4, fontSize: 14, fontFamily: FONT_MEDIUM },
  roomWarning: { color: theme.colors.warning, fontSize: 13, fontFamily: FONT_SEMIBOLD, fontWeight: '600', marginTop: 6 },
  tenantRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  tenant: { color: theme.colors.secondary, fontSize: 14, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
  roomBtn: { marginTop: 10, alignSelf: 'flex-start' },
  docCard: { marginBottom: theme.spacing.sm },
  docExpired: { borderColor: theme.colors.error, backgroundColor: theme.colors.errorLight },
  docTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  docIcon: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  docName: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  docType: { color: theme.colors.textMuted, fontSize: 13, textTransform: 'capitalize', marginTop: 2, fontFamily: FONT_MEDIUM },
  docExpiry: { color: theme.colors.warning, fontSize: 12, marginTop: 4, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
  docExpiryBad: { color: theme.colors.error },
  missingDocs: { backgroundColor: theme.colors.warningLight, borderColor: theme.colors.warning },
  missingTitle: { fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.warning },
  missingBody: { fontSize: 14, color: theme.colors.textSecondary, marginTop: 6, lineHeight: 20, fontFamily: FONT_MEDIUM },
});

import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, DataTable, StatCard, StatGrid, StatusChip, Td, Th, humanize } from "@/components/ui/primitives";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import {
  fetchDataSubjectRequests,
  fetchDpiaRegister,
  fetchPrivacyDashboard,
  fetchPrivacyInventory,
  fetchPrivacyRisks,
} from "@/lib/privacyApi";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { BootstrapPrivacyButton } from "./BootstrapPrivacyButton";

const READ = ["privacy.read", "privacy.manage"];

function whenLabel(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/London" }).format(date);
}

export default async function PrivacyPage() {
  const session = await requireAuthenticatedSession("/dashboard/privacy");
  if (session.authorization && !canAny(session.authorization.permissions, READ)) {
    redirect("/unauthorized");
  }
  const orgId = session.authorization?.active_organisation_id;
  if (!orgId) {
    return <EmptyState title="Choose an organisation" description="Select the organisation you're working in to see privacy records." />;
  }
  if (!isAuth0Configured() || !auth0) {
    return (
      <EmptyState
        title="Sign-in not configured"
        description="Sign-in isn't set up in this environment yet, so privacy records can't load."
      />
    );
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) return <ErrorState description="We couldn't confirm your sign-in. Please sign in again." retryHref="/dashboard/privacy" />;
  const canManage = canAny(session.authorization?.permissions ?? [], ["privacy.manage"]);
  const auth = { accessToken: token, organisationId: orgId, role: session.authorization?.active_role };

  let dash: Record<string, unknown>;
  let inventory: Record<string, unknown>[] = [];
  let dpia: Record<string, unknown>[] = [];
  let requests: Record<string, unknown>[] = [];
  let risks: Record<string, unknown>[] = [];
  try {
    [dash, inventory, dpia, requests, risks] = await Promise.all([
      fetchPrivacyDashboard(auth),
      fetchPrivacyInventory(auth),
      fetchDpiaRegister(auth),
      fetchDataSubjectRequests(auth),
      fetchPrivacyRisks(auth),
    ]);
  } catch {
    return (
      <ErrorState
        title="Couldn't load privacy records"
        description="Something went wrong on our side. Please try again."
        retryHref="/dashboard/privacy"
      />
    );
  }

  const gate = (dash.room_occupancy_privacy_gate ?? {}) as Record<string, unknown>;
  const notice =
    typeof dash.legal_approval_notice === "string"
      ? dash.legal_approval_notice
      : "Technical records only. They are not a legal certification.";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Platform"
        title="Privacy"
        description={notice}
        actions={
          canManage && inventory.length === 0 ? <BootstrapPrivacyButton {...auth} /> : null
        }
      />
      <StatGrid>
        <StatCard label="Inventory items" value={String(dash.inventory_item_count ?? inventory.length)} />
        <StatCard label="Open requests" value={String(dash.open_data_subject_requests ?? 0)} tone="amber" />
        <StatCard label="Open risks" value={String(dash.open_privacy_risks ?? 0)} tone="red" />
        <StatCard label="Occupancy" value={humanize(String(dash.occupancy_live_status ?? "unknown"))} />
      </StatGrid>
      <Card>
        <h2 className="text-base font-semibold text-slate-900">Room occupancy gate</h2>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-600">
          <span>Assessment</span>
          <StatusChip status={String(gate.dpia_status ?? "unknown")} />
          <span>{gate.gate_complete ? "Gate complete" : "Gate incomplete"}</span>
        </div>
        {typeof gate.privacy_notice === "string" && gate.privacy_notice ? (
          <p className="mt-3 text-sm text-slate-600">{gate.privacy_notice}</p>
        ) : null}
      </Card>

      {dpia.length === 0 ? (
        <EmptyState title="No assessments yet" description="Impact assessments will be listed here once they are recorded." />
      ) : (
        <DataTable caption="Privacy assessments">
          <thead>
            <tr>
              <Th>Activity</Th>
              <Th>Reviewer</Th>
              <Th>Due</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {dpia.map((row) => (
              <tr key={String(row.id)}>
                <Td className="font-semibold text-slate-900">{String(row.title || "Assessment")}</Td>
                <Td>{String(row.approved_by_name || row.responsible_reviewer || "—")}</Td>
                <Td className="whitespace-nowrap">{whenLabel(row.review_due_at)}</Td>
                <Td>
                  <StatusChip status={String(row.status ?? "")} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}
      <p className="text-xs text-slate-500">
        Showing {dpia.length === 0 ? "0" : `1–${dpia.length}`} of {dpia.length} assessments
      </p>

      {inventory.length === 0 ? null : (
        <>
          <DataTable caption="Data inventory">
            <thead>
              <tr>
                <Th>Record</Th>
                <Th>Retention</Th>
                <Th>Lawful basis</Th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((row) => (
                <tr key={String(row.id)}>
                  <Td className="font-semibold text-slate-900">{String(row.title || "Record")}</Td>
                  <Td>{row.retention_period_days == null ? "—" : `${String(row.retention_period_days)} days`}</Td>
                  <Td>
                    <StatusChip status={row.lawful_basis_confirmed ? "confirmed" : "pending"}>
                      {row.lawful_basis_confirmed ? "Confirmed" : "Pending"}
                    </StatusChip>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          <p className="text-xs text-slate-500">
            Showing 1–{inventory.length} of {inventory.length} inventory items
          </p>
        </>
      )}

      {requests.length === 0 ? (
        <EmptyState title="No data subject requests" description="Requests from people about their data will appear here." />
      ) : (
        <DataTable caption="Data subject requests">
          <thead>
            <tr>
              <Th>Person</Th>
              <Th>Request</Th>
              <Th>Due</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {requests.map((row) => (
              <tr key={String(row.id)}>
                <Td className="font-semibold text-slate-900">{String(row.subject_label || "Person")}</Td>
                <Td>{humanize(String(row.request_category ?? ""))}</Td>
                <Td className="whitespace-nowrap">{whenLabel(row.due_at)}</Td>
                <Td>
                  <StatusChip status={String(row.status ?? "")} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      )}

      {risks.length > 0 ? (
        <DataTable caption="Privacy risks">
          <thead>
            <tr>
              <Th>Risk</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {risks.map((row) => (
              <tr key={String(row.id)}>
                <Td className="font-semibold text-slate-900">
                  {String(row.title || row.summary || row.description || "Risk")}
                </Td>
                <Td>
                  <StatusChip status={String(row.status ?? "")} />
                </Td>
              </tr>
            ))}
          </tbody>
        </DataTable>
      ) : null}
    </div>
  );
}

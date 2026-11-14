import type { PlatformOrganisation } from "@/lib/platformGovernanceApi";

type Props = {
  organisations: PlatformOrganisation[];
};

export function OrganisationsTable({ organisations }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <caption className="sr-only">Platform organisations</caption>
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Slug</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">ID</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {organisations.map((org) => (
            <tr key={org.id} className="text-slate-800">
              <td className="px-4 py-3 font-medium">{org.name}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-600">{org.slug}</td>
              <td className="px-4 py-3 capitalize text-slate-700">{org.status}</td>
              <td className="px-4 py-3 font-mono text-xs text-slate-500">{org.id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
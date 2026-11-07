/** Pure helpers for tenant timeline UI (testable without React). */

export function activityBadgeClass(type: string): string {
  switch (type) {
    case "daily_log":
      return "bg-slate-100 text-slate-800";
    case "handover":
      return "bg-amber-50 text-amber-900";
    case "tenant_visit":
      return "bg-teal-50 text-teal-900";
    case "meeting":
      return "bg-indigo-50 text-indigo-900";
    case "appointment":
      return "bg-violet-50 text-violet-900";
    case "tenant_follow_up":
      return "bg-orange-50 text-orange-900";
    case "complaint":
    case "complaint_event":
      return "bg-rose-50 text-rose-900";
    case "maintenance":
    case "maintenance_event":
      return "bg-emerald-50 text-emerald-900";
    default:
      return "bg-slate-50 text-slate-700";
  }
}

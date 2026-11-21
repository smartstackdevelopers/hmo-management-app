"use server";

import { revalidatePath } from "next/cache";
import { auth0 } from "@/lib/auth0";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function token(): Promise<string> {
  const result = await auth0?.getAccessToken();
  const value = result?.token;
  if (!value) throw new Error("Not authenticated");
  return value;
}

export async function approveRegistrationAction(formData: FormData) {
  const requestId = String(formData.get("request_id") || "");
  const access = await token();
  await fetch(`${API_BASE}/api/v1/auth/registration-requests/${requestId}/approve`, {
    method: "POST",
    headers: { Authorization: `Bearer ${access}`, Accept: "application/json" },
  });
  revalidatePath("/dashboard/approvals/registrations");
}

export async function rejectRegistrationAction(formData: FormData) {
  const requestId = String(formData.get("request_id") || "");
  const rejectionReason = String(formData.get("rejection_reason") || "");
  const access = await token();
  await fetch(`${API_BASE}/api/v1/auth/registration-requests/${requestId}/reject`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${access}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ rejection_reason: rejectionReason }),
  });
  revalidatePath("/dashboard/approvals/registrations");
}

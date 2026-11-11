"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { geocodeCommunityService } from "@/lib/helpNearMeApi";

export function GeocodeServiceButton({
  accessToken,
  organisationId,
  role,
  serviceId,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  serviceId: string;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-forest-900">Help Near Me coordinates</h2>
      <p className="text-sm text-slate-600">
        Geocode from a UK postcode in the address. Coordinates are never invented.
      </p>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {message ? <p className="text-sm text-teal-800">{message}</p> : null}
      <button
        type="button"
        disabled={pending}
        className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
        onClick={async () => {
          setPending(true);
          setError(null);
          setMessage(null);
          try {
            const result = await geocodeCommunityService({
              accessToken,
              organisationId,
              role,
              serviceId,
            });
            setMessage(
              `Geocoded (${result.geocode_status}): ${result.latitude}, ${result.longitude}`,
            );
            router.refresh();
          } catch (err) {
            setError(err instanceof Error ? err.message : "Geocoding failed");
          } finally {
            setPending(false);
          }
        }}
      >
        {pending ? "Geocoding…" : "Geocode from address postcode"}
      </button>
    </div>
  );
}

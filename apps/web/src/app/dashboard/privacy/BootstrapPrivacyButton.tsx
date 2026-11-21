"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { btnPrimary } from "@/components/ui/primitives";
import { bootstrapPrivacyCatalog } from "@/lib/privacyApi";

export function BootstrapPrivacyButton({
  accessToken,
  organisationId,
  role,
}: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      <button
        type="button"
        className={btnPrimary}
        disabled={pending}
        onClick={async () => {
          setPending(true);
          setError(null);
          try {
            await bootstrapPrivacyCatalog({ accessToken, organisationId, role });
            router.refresh();
          } catch {
            setError("The privacy catalogue could not be created.");
          } finally {
            setPending(false);
          }
        }}
      >
        {pending ? "Creating…" : "Create inventory templates"}
      </button>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}

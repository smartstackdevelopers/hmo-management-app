import type { ReactNode } from "react";
import { CommunicationsNav } from "./CommunicationsNav";

export default function CommunicationsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <CommunicationsNav />
      {children}
    </div>
  );
}

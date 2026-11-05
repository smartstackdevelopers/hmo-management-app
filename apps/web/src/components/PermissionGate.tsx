import type { ReactNode } from "react";
import { can, type PermissionId } from "@/lib/rbac";

type PermissionGateProps = {
  permissions: PermissionId[] | undefined;
  require: PermissionId | PermissionId[];
  children: ReactNode;
  fallback?: ReactNode;
  mode?: "hide" | "disable";
};

/**
 * Hides or disables UI when the caller lacks a permission.
 * Never use this as the only security control — API checks are mandatory.
 */
export function PermissionGate({
  permissions,
  require,
  children,
  fallback = null,
  mode = "hide",
}: PermissionGateProps) {
  const required = Array.isArray(require) ? require : [require];
  const allowed = required.every((permission) => can(permissions, permission));

  if (allowed) {
    return <>{children}</>;
  }

  if (mode === "disable" && typeof children === "object" && children !== null) {
    return (
      <div aria-disabled="true" className="pointer-events-none opacity-50">
        {children}
      </div>
    );
  }

  return <>{fallback}</>;
}

import Link from "next/link";

/** WCAG 2.4.1 bypass block — visible on keyboard focus only. */
export function SkipLink() {
  return (
    <Link href="#main-content" className="skip-link">
      Skip to main content
    </Link>
  );
}

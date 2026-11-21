/** Turns API auth failures into plain-English copy. Raw API text is never shown to users. */

type Kind = "login" | "register";

const FALLBACK: Record<Kind, string> = {
  login: "We couldn’t sign you in. Check your email and password and try again.",
  register: "We couldn’t send your request. Check the form and try again.",
};

const RULES: { match: RegExp; message: string }[] = [
  { match: /pending|not\s+approved|awaiting/i, message: "Your account is still waiting for approval. We’ll let you know when it’s ready." },
  { match: /rejected|declined/i, message: "Your access request was not approved. Contact your housing provider for help." },
  { match: /suspended|disabled|inactive|locked/i, message: "This account is not active. Contact your housing provider." },
  { match: /invalid\s+credentials|incorrect|wrong\s+password|unauthori[sz]ed|401/i, message: "That email and password don’t match. Try again or reset your password." },
  { match: /already\s+(exists|registered)|duplicate/i, message: "An account with this email already exists. Try signing in instead." },
  { match: /passwords?\s+(do\s+not|don.t)\s+match/i, message: "The two passwords don’t match." },
  { match: /password/i, message: "Choose a password with at least 8 characters." },
  { match: /email/i, message: "Enter a valid email address." },
  { match: /organisation|organization|slug/i, message: "We couldn’t find that organisation. Check the code or leave it blank." },
  { match: /invitation/i, message: "That invitation code isn’t valid or has expired." },
  { match: /role/i, message: "That role can’t be requested here. Choose another role." },
  { match: /terms|privacy/i, message: "Please accept the terms of use and privacy notice." },
  { match: /too\s+many|rate/i, message: "Too many attempts. Wait a minute and try again." },
];

function extractDetail(raw: string): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown; message?: unknown };
    const detail = parsed.detail ?? parsed.message;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join(" ");
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
  } catch {
    // Not JSON — fall through to the raw text.
  }
  return raw;
}

export function friendlyAuthError(raw: string | undefined, kind: Kind): string | null {
  if (!raw) return null;
  const detail = extractDetail(raw);
  for (const rule of RULES) {
    if (rule.match.test(detail)) return rule.message;
  }
  return FALLBACK[kind];
}

type BrandMarkProps = {
  size?: "sm" | "md" | "lg";
  inverted?: boolean;
};

const SIZES = {
  sm: "h-8 w-8 rounded-lg",
  md: "h-9 w-9 rounded-xl",
  lg: "h-12 w-12 rounded-2xl",
};

export function BrandMark({ size = "md", inverted = false }: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center ${SIZES[size]} ${
        inverted ? "bg-white text-brand-700" : "bg-brand-700 text-white"
      }`}
    >
      <svg viewBox="0 0 48 48" className="h-3/4 w-3/4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
        <path d="M24 11 L36 20.5 V33 H29.5 V25 H18.5 V33 H12 V20.5 Z" strokeWidth="2.6" />
        <path d="M19 25.5 L22.8 29.5 L31.5 19.5" strokeWidth="3" className={inverted ? "text-brand-400" : "text-brand-200"} stroke="currentColor" />
      </svg>
    </span>
  );
}

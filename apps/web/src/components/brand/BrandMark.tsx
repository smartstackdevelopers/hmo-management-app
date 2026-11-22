type BrandMarkProps = {
  size?: "sm" | "md" | "lg";
  inverted?: boolean;
};

const SIZES = {
  sm: "h-8 w-8 rounded-lg text-base",
  md: "h-9 w-9 rounded-xl text-lg",
  lg: "h-12 w-12 rounded-xl text-2xl",
};

export function BrandMark({ size = "md", inverted = false }: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center font-bold leading-none ${SIZES[size]} ${
        inverted ? "bg-white text-brand-700" : "bg-brand-600 text-white"
      }`}
    >
      H
    </span>
  );
}

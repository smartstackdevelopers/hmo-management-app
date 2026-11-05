type PageHeaderProps = {
  title: string;
  description?: string;
  eyebrow?: string;
};

export function PageHeader({ title, description, eyebrow }: PageHeaderProps) {
  return (
    <header className="mb-8">
      {eyebrow ? (
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-800">
          {eyebrow}
        </p>
      ) : null}
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-forest-900">{title}</h1>
      {description ? (
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-700">{description}</p>
      ) : null}
    </header>
  );
}

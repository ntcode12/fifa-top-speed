export default function Section({
  eyebrow,
  title,
  sub,
  children,
}: {
  eyebrow: string;
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-14">
      <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--indigo)]">
        {eyebrow}
      </div>
      <h2 className="mt-2 text-[23px] font-extrabold tracking-tight text-[#f2f5fb] max-sm:text-[19px]">
        {title}
      </h2>
      <p className="mt-1 mb-5 max-w-[720px] text-[12.5px] leading-relaxed text-[var(--dim)]">
        {sub}
      </p>
      {children}
    </section>
  );
}

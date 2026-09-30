export function Flame({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 2c1 6 8 9 8 17a8 8 0 0 1-16 0c0-4 2-6 4-8 0 3 1 4 2 4 1-4-1-8 2-13z" fill="#FF8A3D" />
      <path d="M16 15c1 3 4 4 4 8a4 4 0 0 1-8 0c0-3 3-4 4-8z" fill="#5B8DEF" />
    </svg>
  );
}

export function Brand({ big = false }: { big?: boolean }) {
  return (
    <span className={big ? "brand brand-big" : "brand"}>
      <Flame className="flame" />
      Prometheus
    </span>
  );
}

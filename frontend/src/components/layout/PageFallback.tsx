export function PageFallback() {
  return (
    <div className="mx-auto flex max-w-6xl items-center justify-center px-4 py-24">
      <div
        className="size-8 animate-spin rounded-full border-2 border-sand-300 border-t-brand-600"
        role="status"
        aria-label="Cargando"
      />
    </div>
  );
}

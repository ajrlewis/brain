export default function Loading() {
  return (
    <div id="content" className="content" aria-busy="true">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-card" />
      <span className="sr-only">Loading knowledge</span>
    </div>
  );
}

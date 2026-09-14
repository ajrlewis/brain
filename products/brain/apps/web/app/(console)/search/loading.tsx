export default function SearchLoading() {
  return (
    <div id="content" className="content" aria-busy="true">
      <p className="eyebrow">Authorized retrieval</p>
      <h1>Search</h1>
      <div className="card search-loading">Searching authorized knowledge…</div>
    </div>
  );
}

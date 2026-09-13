import Link from "next/link";
import { Badge, Breadcrumbs, Card } from "@/components/ui";
import { ApiError, searchPages } from "@/lib/api";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const rawQuery = (await searchParams).q ?? "";
  const query = rawQuery.trim();
  const invalid = rawQuery.length > 500 || (rawQuery.length > 0 && !query);
  let response = null;
  let error: ApiError | null = null;
  if (query && !invalid) {
    try {
      response = await searchPages(query);
    } catch (caught) {
      error = caught instanceof ApiError ? caught : new ApiError(503, "Search is unavailable.");
    }
  }
  return (
    <div id="content" className="content">
      <Breadcrumbs items={[{ label: "Search" }]} />
      <div className="title-row">
        <div>
          <p className="eyebrow">Authorized retrieval</p>
          <h1>Search</h1>
          <p className="lede">Find current knowledge you are permitted to inspect.</p>
        </div>
      </div>
      <Card>
        <form className="search-form" action="/search" method="get">
          <label htmlFor="search-query">Search knowledge</label>
          <div>
            <input
              id="search-query"
              name="q"
              defaultValue={rawQuery}
              maxLength={500}
              placeholder="Search pages, facts, and headings"
            />
            <button type="submit">Search</button>
          </div>
        </form>
      </Card>
      <div className="search-results" aria-live="polite">
        {invalid ? (
          <Card className="state-error">
            <Badge tone="danger">Invalid</Badge>
            <h2>Enter a meaningful query</h2>
            <p>Queries must contain text and be no longer than 500 characters.</p>
          </Card>
        ) : error ? (
          <Card className="state-error">
            <Badge tone="danger">{error.status === 403 ? "Denied" : "Error"}</Badge>
            <h2>{error.status === 403 ? "Search access denied" : "Search unavailable"}</h2>
            <p>{error.message}</p>
          </Card>
        ) : !query ? (
          <Card>
            <h2>Start with a question or phrase</h2>
            <p className="muted">Only authorized current Page versions can appear.</p>
          </Card>
        ) : response?.results.length === 0 ? (
          <Card>
            <h2>No authorized results</h2>
            <p className="muted">Try a different phrase or fewer terms.</p>
          </Card>
        ) : (
          response?.results.map((result) => (
            <Card className="search-result" key={result.chunk_id}>
              <div>
                <p className="eyebrow">{result.heading_path.join(" / ") || "Page"}</p>
                <h2>
                  <Link href={`/pages/${result.page_id}`}>{result.title}</Link>
                </h2>
                <p>{result.snippet}</p>
              </div>
              <small>
                {result.path} · version {result.page_version_id.slice(0, 8)} · chunk{" "}
                {result.chunk_position + 1}
              </small>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

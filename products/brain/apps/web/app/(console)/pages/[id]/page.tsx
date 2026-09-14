import { notFound } from "next/navigation";
import { ApiError, getPage } from "@/lib/api";
import { Markdown } from "@/components/markdown";
import { Badge, Breadcrumbs, Card, ErrorState } from "@/components/ui";
export default async function PageDetailRoute({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let page;
  try {
    page = await getPage(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return (
      <div id="content" className="content">
        <Breadcrumbs
          items={[
            { label: "Knowledge", href: "/pages" },
            { label: "Unavailable" },
          ]}
        />
        <ErrorState
          message={
            error instanceof ApiError
              ? error.message
              : "Knowledge is unavailable."
          }
        />
      </div>
    );
  }
  const version = page.current_version;
  return (
    <div id="content" className="content">
      <Breadcrumbs
        items={[{ label: "Knowledge", href: "/pages" }, { label: page.title }]}
      />
      <div className="title-row">
        <div>
          <p className="eyebrow">Page · version {version.version}</p>
          <h1>{page.title}</h1>
        </div>
        <Badge tone="success">Current</Badge>
      </div>
      <div className="detail-grid">
        <Card>
          <Markdown content={version.content_markdown} />
        </Card>
        <aside>
          <Card>
            <h2>Provenance</h2>
            <dl className="metadata">
              <div>
                <dt>Content hash</dt>
                <dd>
                  <code>{version.content_hash.slice(0, 12)}</code>
                </dd>
              </div>
              <div>
                <dt>Published</dt>
                <dd>
                  <time dateTime={version.created_at}>
                    {new Date(version.created_at).toLocaleDateString("en-GB", {
                      dateStyle: "medium",
                    })}
                  </time>
                </dd>
              </div>
            </dl>
            {version.provenance.length ? (
              <ul className="sources">
                {version.provenance.map(({ source, relationship }) => (
                  <li key={source.id}>
                    <strong>{source.title}</strong>
                    <span>
                      {relationship} · {source.source_type}
                    </span>
                    {source.canonical_uri && (
                      <a href={source.canonical_uri} rel="noreferrer noopener">
                        View source
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No visible sources.</p>
            )}
          </Card>
        </aside>
      </div>
    </div>
  );
}

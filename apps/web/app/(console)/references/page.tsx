import { getSources } from "@/lib/api";
import { Badge, Breadcrumbs, Card, EmptyState } from "@/components/ui";
export default async function References() {
  const sources = await getSources();
  return (
    <div id="content" className="content">
      <Breadcrumbs items={[{ label: "Reference files" }]} />
      <p className="eyebrow">Visible provenance</p>
      <h1>Reference files</h1>
      {sources.length === 0 ? (
        <EmptyState />
      ) : (
        <Card>
          <ul className="reference-list">
            {sources.map((source) => (
              <li key={source.id}>
                <div>
                  <strong>{source.title}</strong>
                  <span>{source.source_type}</span>
                </div>
                <Badge
                  tone={source.status === "active" ? "success" : "warning"}
                >
                  {source.status}
                </Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

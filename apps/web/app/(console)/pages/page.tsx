import Link from "next/link";
import { ApiError, getPages } from "@/lib/api";
import {
  Badge,
  Breadcrumbs,
  Card,
  EmptyState,
  ErrorState,
} from "@/components/ui";
export default async function Pages() {
  let pages;
  try {
    pages = await getPages();
  } catch (error) {
    return (
      <div id="content" className="content">
        <Breadcrumbs items={[{ label: "Knowledge" }]} />
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
  return (
    <div id="content" className="content">
      <Breadcrumbs items={[{ label: "Knowledge" }]} />
      <div className="title-row">
        <div>
          <p className="eyebrow">Authorized inventory</p>
          <h1>Knowledge</h1>
          <p className="lede">
            Browse governed pages available to your Brain identity.
          </p>
        </div>
        <Badge tone="success">{pages.length} available</Badge>
      </div>
      {pages.length === 0 ? (
        <EmptyState />
      ) : (
        <Card>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Folder</th>
                  <th>Version</th>
                </tr>
              </thead>
              <tbody>
                {pages.map((page) => {
                  const segments = page.path.split("/");
                  return (
                    <tr key={page.id}>
                      <td>
                        <Link className="page-link" href={`/pages/${page.id}`}>
                          {page.title}
                        </Link>
                        <small>{page.slug}</small>
                      </td>
                      <td>{segments.slice(0, -1).join(" / ") || "Root"}</td>
                      <td>
                        <code>{page.content_hash.slice(0, 8)}</code>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

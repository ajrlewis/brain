import { ButtonLink, Card } from "@/components/ui";
export default function NotFound() {
  return (
    <div id="content" className="content">
      <Card>
        <p className="eyebrow">404</p>
        <h1>Page not found</h1>
        <p>The page is missing or is not visible to your identity.</p>
        <ButtonLink href="/pages">Back to knowledge</ButtonLink>
      </Card>
    </div>
  );
}

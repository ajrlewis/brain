import { getSkills } from "@/lib/api";
import { Breadcrumbs, Card, EmptyState } from "@/components/ui";
export default async function Skills() {
  const skills = await getSkills();
  return (
    <div id="content" className="content">
      <Breadcrumbs items={[{ label: "Skills" }]} />
      <p className="eyebrow">Reusable capabilities</p>
      <h1>Skills</h1>
      {skills.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="card-grid">
          {skills.map((skill) => (
            <Card key={skill.id}>
              <h2>{skill.name}</h2>
              <p className="muted">{skill.slug}</p>
              <code>{skill.content_hash.slice(0, 8)}</code>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

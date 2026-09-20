"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { Badge, Button, Card } from "@/components/ui";
import { applicationsApi, scholarshipsApi } from "@/lib/api";
import { eligibilityLabel, formatDate } from "@/lib/utils";

function DetailContent() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const qc = useQueryClient();
  const { data: s, isLoading } = useQuery({
    queryKey: ["scholarship", id],
    queryFn: () => scholarshipsApi.get(id),
  });
  const save = useMutation({
    mutationFn: () => scholarshipsApi.save(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scholarship", id] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
  const start = useMutation({
    mutationFn: () => applicationsApi.create(id, "preparing"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  if (isLoading || !s) return <p className="text-muted-foreground">Loading…</p>;

  const match = s.match;
  const fact = (key: string) => s.fact_statuses?.[key];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/scholarships" className="text-sm text-muted-foreground hover:underline">
            ← Scholarships
          </Link>
          <h1 className="mt-2 text-4xl text-primary">{s.name}</h1>
          <p className="mt-2 text-muted-foreground">
            {s.provider}
            {s.host_institution ? ` · ${s.host_institution}` : ""}
            {s.country ? ` · ${s.country}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {s.verification_status === "verified" && (
            <Badge className="border-success/40 text-success">Verified from official source</Badge>
          )}
          <Button variant="outline" onClick={() => save.mutate()} disabled={save.isPending}>
            Save
          </Button>
          <Button onClick={() => start.mutate()} disabled={start.isPending}>
            Start Application
          </Button>
        </div>
      </div>

      <Section title="Overview">
        <p className="text-sm leading-relaxed text-muted-foreground">{s.description || "No description extracted."}</p>
        {s.official_url && (
          <a href={s.official_url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm text-primary underline">
            Open official page
          </a>
        )}
      </Section>

      <Section title="Funding">
        <FactList
          items={[
            ["Type", s.funding_type.replace(/_/g, " "), fact("funding")],
            ["Tuition", boolLabel(s.tuition_coverage), fact("funding")],
            ["Stipend", s.stipend || "Unknown", fact("funding")],
            ["Travel", boolLabel(s.travel_coverage), fact("funding")],
            ["Insurance", boolLabel(s.insurance_coverage), fact("funding")],
            ["Accommodation", boolLabel(s.accommodation_coverage), fact("funding")],
          ]}
        />
      </Section>

      <Section title="Eligibility">
        <FactList
          items={[
            ["Nationalities", (s.eligible_nationalities || []).join(", ") || "Unknown", fact("eligible_nationalities")],
            ["Degree levels", (s.degree_levels || []).join(", ") || "Unknown", null],
            ["Fields", (s.fields_of_study || []).join(", ") || "Unknown", null],
            ["Minimum GPA", s.minimum_gpa?.toString() || "Unknown", fact("minimum_gpa")],
            ["Required degree", s.required_degree || "Unknown", null],
            ["Language", s.language_requirements || "Unknown", fact("language_requirements")],
            ["Age", s.age_requirement || "Unknown", null],
          ]}
        />
      </Section>

      <Section title="Required Documents">
        <ul className="space-y-1 text-sm">
          {(s.documents || []).map((d) => (
            <li key={d.id}>□ {d.name}</li>
          ))}
          {(s.documents || []).length === 0 && <li className="text-muted-foreground">None extracted yet</li>}
        </ul>
      </Section>

      <Section title="Application Process">
        <p className="whitespace-pre-wrap text-sm text-muted-foreground">
          {s.application_process || "Not extracted from source."}
        </p>
      </Section>

      <Section title="Deadline">
        <p className="text-lg font-medium">{formatDate(s.application_deadline)}</p>
        {s.days_remaining != null && (
          <p className="text-sm text-muted-foreground">{s.days_remaining} days remaining</p>
        )}
        {fact("deadline") === "verified" && s.official_url && (
          <p className="mt-2 text-sm text-success">
            Verified from: Official scholarship page
          </p>
        )}
      </Section>

      <Section title="AI Eligibility Analysis">
        {match ? (
          <div className="space-y-3 text-sm">
            <Badge>{eligibilityLabel(match.status)}</Badge>
            <p className="text-muted-foreground">{match.reasoning_summary}</p>
            <ReqGroup title="Matched" items={match.matched_requirements} prefix="✓" />
            <ReqGroup title="Missing" items={match.missing_requirements} prefix="⚠" />
            <ReqGroup title="Failed" items={match.failed_requirements} prefix="✗" />
            <ReqGroup title="Unknown" items={match.unknown_requirements} prefix="?" />
            <p className="text-muted-foreground">Confidence: {(match.confidence * 100).toFixed(0)}%</p>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Not evaluated for your profile yet.</p>
        )}
      </Section>

      <Section title="Sources">
        <ul className="space-y-2 text-sm">
          {(s.sources || []).map((src) => (
            <li key={src.id}>
              <a href={src.url} className="text-primary underline" target="_blank" rel="noreferrer">
                {src.title || src.url}
              </a>
              {src.is_official && <span className="ml-2 text-success">Official</span>}
              <span className="ml-2 text-muted-foreground">trust {src.trust_score}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Verification History">
        <ul className="space-y-2 text-sm text-muted-foreground">
          {(s.changes || []).map((c) => (
            <li key={c.id}>
              <span className="font-medium text-foreground">{c.change_type.replace(/_/g, " ")}</span>
              : {c.field_name} {c.previous_value} → {c.new_value}
            </li>
          ))}
          {(s.changes || []).length === 0 && <li>No changes recorded yet.</li>}
        </ul>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="text-xl text-primary">{title}</h2>
      <div className="mt-3">{children}</div>
    </Card>
  );
}

function FactList({
  items,
}: {
  items: Array<[string, string, string | null | undefined]>;
}) {
  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      {items.map(([label, value, status]) => (
        <div key={label}>
          <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
          <dd className="text-sm">
            {value}
            {status && (
              <span className="ml-2 text-xs text-muted-foreground">({status})</span>
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ReqGroup({
  title,
  items,
  prefix,
}: {
  title: string;
  items: string[];
  prefix: string;
}) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="font-medium">{title}</p>
      <ul className="mt-1 space-y-1 text-muted-foreground">
        {items.map((i) => (
          <li key={i}>
            {prefix} {i}
          </li>
        ))}
      </ul>
    </div>
  );
}

function boolLabel(v?: boolean | null) {
  if (v === true) return "Yes";
  if (v === false) return "No";
  return "Unknown";
}

export default function ScholarshipDetailPage() {
  return (
    <AuthGate>
      <AppShell>
        <DetailContent />
      </AppShell>
    </AuthGate>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { Badge, Button, Card, Input } from "@/components/ui";
import { scholarshipsApi } from "@/lib/api";
import { eligibilityLabel, formatDate } from "@/lib/utils";

function ScholarshipsContent() {
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("");
  const [fullyFunded, setFullyFunded] = useState(false);
  const [field, setField] = useState("");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["scholarships", q, country, fullyFunded, field],
    queryFn: () =>
      scholarshipsApi.list({
        q: q || undefined,
        country: country || undefined,
        field: field || undefined,
        fully_funded: fullyFunded ? "true" : undefined,
      }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl text-primary">Scholarships</h1>
        <p className="mt-2 text-muted-foreground">
          Browse matched opportunities. Prefer verified official sources.
        </p>
      </div>

      <Card className="grid gap-3 p-4 md:grid-cols-4">
        <Input placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} />
        <Input placeholder="Country" value={country} onChange={(e) => setCountry(e.target.value)} />
        <Input placeholder="Field" value={field} onChange={(e) => setField(e.target.value)} />
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={fullyFunded}
              onChange={(e) => setFullyFunded(e.target.checked)}
            />
            Fully funded
          </label>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            Apply
          </Button>
        </div>
      </Card>

      {isLoading && <p className="text-muted-foreground">Loading scholarships…</p>}
      <div className="grid gap-4">
        {data?.items.map((s) => (
          <Card key={s.id} className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Link href={`/scholarships/${s.id}`} className="text-xl hover:underline">
                  {s.name}
                </Link>
                <p className="mt-1 text-sm text-muted-foreground">
                  {s.provider}
                  {s.country ? ` · ${s.country}` : ""} · Deadline {formatDate(s.application_deadline)}
                  {s.days_remaining != null ? ` (${s.days_remaining}d)` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {s.verification_status === "verified" && (
                  <Badge className="border-success/40 text-success">Verified from official source</Badge>
                )}
                <Badge>{eligibilityLabel(s.eligibility_status)}</Badge>
                <Badge className="bg-secondary">{s.funding_type.replace(/_/g, " ")}</Badge>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              {(s.fields_of_study || []).slice(0, 4).join(" · ") || "Fields not specified"}
            </p>
          </Card>
        ))}
        {data && data.items.length === 0 && (
          <Card className="p-6 text-muted-foreground">No scholarships match these filters.</Card>
        )}
      </div>
    </div>
  );
}

export default function ScholarshipsPage() {
  return (
    <AuthGate>
      <AppShell>
        <ScholarshipsContent />
      </AppShell>
    </AuthGate>
  );
}

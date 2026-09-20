"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { Badge, Button, Card } from "@/components/ui";
import { applicationsApi } from "@/lib/api";
import type { Application } from "@/types";
import Link from "next/link";

const COLUMNS = [
  "saved",
  "preparing",
  "ready_to_apply",
  "applied",
  "interview",
  "awarded",
  "rejected",
  "withdrawn",
] as const;

const LABELS: Record<string, string> = {
  saved: "Saved",
  preparing: "Preparing",
  ready_to_apply: "Ready to Apply",
  applied: "Applied",
  interview: "Interview",
  awarded: "Awarded",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

function PipelineContent() {
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: applicationsApi.list,
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      applicationsApi.update(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  const toggleDoc = useMutation({
    mutationFn: ({
      appId,
      docId,
      is_complete,
    }: {
      appId: string;
      docId: string;
      is_complete: boolean;
    }) => applicationsApi.updateDocument(appId, docId, is_complete),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["applications"] }),
  });

  if (isLoading) return <p className="text-muted-foreground">Loading pipeline…</p>;

  const byStatus = (status: string) => data.filter((a) => a.status === status);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl text-primary">Application Pipeline</h1>
        <p className="mt-2 text-muted-foreground">
          Track every scholarship from saved to awarded. Mark documents as you go.
        </p>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => (
          <div key={col} className="min-w-[260px] flex-1">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {LABELS[col]}
            </h2>
            <div className="space-y-3">
              {byStatus(col).map((app) => (
                <AppCard
                  key={app.id}
                  app={app}
                  onStatus={(status) => updateStatus.mutate({ id: app.id, status })}
                  onToggleDoc={(docId, is_complete) =>
                    toggleDoc.mutate({ appId: app.id, docId, is_complete })
                  }
                />
              ))}
              {byStatus(col).length === 0 && (
                <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                  Empty
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AppCard({
  app,
  onStatus,
  onToggleDoc,
}: {
  app: Application;
  onStatus: (status: string) => void;
  onToggleDoc: (docId: string, complete: boolean) => void;
}) {
  return (
    <Card className="p-4">
      <Link
        href={`/scholarships/${app.scholarship_id}`}
        className="font-medium hover:underline"
      >
        {app.scholarship?.name || "Scholarship"}
      </Link>
      <p className="mt-1 text-xs text-muted-foreground">
        Readiness: {app.readiness_percent}%
      </p>
      <div className="mt-2 h-1.5 overflow-hidden rounded bg-muted">
        <div
          className="h-full bg-accent transition-all"
          style={{ width: `${app.readiness_percent}%` }}
        />
      </div>
      <ul className="mt-3 max-h-40 space-y-1 overflow-y-auto text-xs">
        {app.documents.map((d) => (
          <li key={d.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={d.is_complete}
              onChange={(e) => onToggleDoc(d.id, e.target.checked)}
            />
            <span>{d.name}</span>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap gap-1">
        {COLUMNS.filter((c) => c !== app.status)
          .slice(0, 3)
          .map((c) => (
            <Button key={c} size="sm" variant="ghost" onClick={() => onStatus(c)}>
              → {LABELS[c]}
            </Button>
          ))}
      </div>
    </Card>
  );
}

export default function ApplicationsPage() {
  return (
    <AuthGate>
      <AppShell>
        <PipelineContent />
      </AppShell>
    </AuthGate>
  );
}

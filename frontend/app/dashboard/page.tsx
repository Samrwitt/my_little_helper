"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { Badge, Button, Card } from "@/components/ui";
import { agentApi, applicationsApi, dashboardApi } from "@/lib/api";
import { eligibilityLabel, formatDate } from "@/lib/utils";

function DashboardContent() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: dashboardApi.get });
  const discover = useMutation({
    mutationFn: () => agentApi.discover(8),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["scholarships"] });
    },
  });

  if (isLoading || !data) {
    return <p className="text-muted-foreground">Loading dashboard…</p>;
  }

  const stats = [
    { label: "Matched Scholarships", value: data.stats.matched_scholarships },
    { label: "Applications In Progress", value: data.stats.applications_in_progress },
    { label: "Deadlines This Month", value: data.stats.deadlines_this_month },
    { label: "Applications Submitted", value: data.stats.applications_submitted },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.18em] text-accent">Scholarship Autopilot</p>
          <h1 className="mt-1 text-4xl text-primary">What should you work on today?</h1>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Matches, missing requirements, and approaching deadlines — managed for you.
          </p>
        </div>
        <Button
          onClick={() => discover.mutate()}
          disabled={discover.isPending}
          className={discover.isPending ? "animate-pulse-soft" : ""}
        >
          {discover.isPending ? "Discovering…" : "Run discovery agent"}
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s, i) => (
          <Card
            key={s.label}
            className="p-4 animate-fade-up"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <p className="text-sm text-muted-foreground">{s.label}</p>
            <p className="mt-2 text-3xl font-semibold text-primary">{s.value}</p>
          </Card>
        ))}
      </div>

      <section>
        <h2 className="text-2xl text-primary">Upcoming Deadlines</h2>
        <div className="mt-4 space-y-4">
          {data.upcoming_deadlines.length === 0 && (
            <Card className="p-6 text-muted-foreground">
              No upcoming deadlines yet. Run discovery or browse scholarships.
            </Card>
          )}
          {data.upcoming_deadlines.map((item) => (
            <Card key={item.scholarship_id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-xl">{item.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Deadline: {formatDate(item.deadline)} ·{" "}
                    <span className="font-medium text-foreground">
                      {item.days_remaining ?? "—"} days remaining
                    </span>
                  </p>
                </div>
                <Badge className="bg-secondary">{eligibilityLabel(item.eligibility_status)}</Badge>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-sm font-medium">Funding</p>
                  <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                    {item.funding.tuition && <li>✓ Tuition</li>}
                    {item.funding.stipend && <li>✓ Monthly stipend</li>}
                    {item.funding.travel && <li>✓ Travel</li>}
                    {item.funding.insurance && <li>✓ Insurance</li>}
                    {!item.funding.tuition && !item.funding.stipend && (
                      <li>See scholarship details</li>
                    )}
                  </ul>
                </div>
                <div>
                  <p className="text-sm font-medium">Missing</p>
                  <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                    {(item.missing_requirements || []).slice(0, 4).map((m) => (
                      <li key={m}>⚠ {m}</li>
                    ))}
                    {(item.missing_requirements || []).length === 0 && <li>No gaps flagged</li>}
                  </ul>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link href={`/scholarships/${item.scholarship_id}`}>
                  <Button variant="outline" size="sm">
                    View Scholarship
                  </Button>
                </Link>
                <Button
                  size="sm"
                  onClick={() =>
                    applicationsApi.create(item.scholarship_id, "preparing").then(() => {
                      qc.invalidateQueries({ queryKey: ["dashboard"] });
                      qc.invalidateQueries({ queryKey: ["applications"] });
                    })
                  }
                >
                  Start Application
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthGate>
      <AppShell>
        <DashboardContent />
      </AppShell>
    </AuthGate>
  );
}

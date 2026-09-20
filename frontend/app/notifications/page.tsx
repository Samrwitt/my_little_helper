"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { Button, Card } from "@/components/ui";
import { notificationsApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

function NotificationsContent() {
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
  });
  const mark = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-4xl text-primary">Notifications</h1>
      {isLoading && <p className="text-muted-foreground">Loading…</p>}
      <div className="space-y-3">
        {data.map((n) => (
          <Card key={n.id} className={`p-4 ${n.is_read ? "opacity-70" : ""}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-medium">{n.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{n.body}</p>
                <p className="mt-2 text-xs text-muted-foreground">{formatDate(n.created_at)}</p>
              </div>
              <div className="flex gap-2">
                {n.link && (
                  <Link href={n.link}>
                    <Button size="sm" variant="outline">
                      Open
                    </Button>
                  </Link>
                )}
                {!n.is_read && (
                  <Button size="sm" variant="ghost" onClick={() => mark.mutate(n.id)}>
                    Mark read
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
        {data.length === 0 && !isLoading && (
          <Card className="p-6 text-muted-foreground">No notifications yet.</Card>
        )}
      </div>
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <AuthGate>
      <AppShell>
        <NotificationsContent />
      </AppShell>
    </AuthGate>
  );
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "@/components/app-shell";
import { AuthGate } from "@/components/auth-gate";
import { Button, Card, Input, Label } from "@/components/ui";
import { profileApi } from "@/lib/api";

function ProfileContent() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["profile"], queryFn: profileApi.get });
  const [form, setForm] = useState({
    nationality: "",
    country_of_residence: "",
    highest_degree: "",
    target_degree: "",
    fields: "",
    graduation_year: "",
    gpa: "",
    work_experience_years: "",
    funding_preference: "",
    preferred_countries: "",
  });
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!data) return;
    setForm({
      nationality: data.nationality || "",
      country_of_residence: data.country_of_residence || "",
      highest_degree: data.highest_degree || "",
      target_degree: data.target_degree || "",
      fields: (data.fields || []).join(", "),
      graduation_year: data.graduation_year?.toString() || "",
      gpa: data.gpa?.toString() || "",
      work_experience_years: data.work_experience_years?.toString() || "",
      funding_preference: data.funding_preference || "",
      preferred_countries: (data.preferred_countries || []).join(", "),
    });
  }, [data]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await profileApi.update({
      nationality: form.nationality,
      country_of_residence: form.country_of_residence,
      highest_degree: form.highest_degree,
      target_degree: form.target_degree,
      fields: form.fields.split(",").map((s) => s.trim()).filter(Boolean),
      graduation_year: Number(form.graduation_year) || undefined,
      gpa: Number(form.gpa) || undefined,
      work_experience_years: Number(form.work_experience_years) || undefined,
      funding_preference: form.funding_preference,
      preferred_countries: form.preferred_countries
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      english_tests: data?.english_tests || { ielts: null, toefl: null },
    });
    setMessage("Profile saved. Eligibility will be recomputed.");
    qc.invalidateQueries({ queryKey: ["profile"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-4xl text-primary">Your profile</h1>
      <Card className="p-6">
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
          {Object.entries(form).map(([key, value]) => (
            <div key={key} className={`space-y-2 ${key === "fields" || key === "preferred_countries" ? "sm:col-span-2" : ""}`}>
              <Label htmlFor={key}>{key.replace(/_/g, " ")}</Label>
              <Input
                id={key}
                value={value}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <div className="sm:col-span-2">
            <Button type="submit">Save profile</Button>
            {message && <p className="mt-2 text-sm text-accent">{message}</p>}
          </div>
        </form>
      </Card>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <AuthGate>
      <AppShell>
        <ProfileContent />
      </AppShell>
    </AuthGate>
  );
}

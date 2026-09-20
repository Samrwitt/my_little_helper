"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { profileApi } from "@/lib/api";
import { Button, Card, Input, Label } from "@/components/ui";

export default function OnboardingPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    nationality: "Ethiopian",
    country_of_residence: "Ethiopia",
    highest_degree: "BSc Computer Science",
    target_degree: "Masters",
    fields: "Computer Science, Artificial Intelligence, Machine Learning, Data Science",
    graduation_year: "2025",
    gpa: "3.5",
    work_experience_years: "2",
    funding_preference: "fully-funded",
    preferred_countries: "",
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
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
        english_tests: { ielts: null, toefl: null },
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-4xl text-primary">Build your scholarship profile</h1>
      <p className="mt-2 text-muted-foreground">
        Enter once. The discovery agent uses this to find and score opportunities continuously.
      </p>
      <Card className="mt-8 p-6">
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
          {(
            [
              ["nationality", "Nationality"],
              ["country_of_residence", "Country of residence"],
              ["highest_degree", "Highest degree"],
              ["target_degree", "Target degree"],
              ["graduation_year", "Graduation year"],
              ["gpa", "GPA (0–4)"],
              ["work_experience_years", "Work experience (years)"],
              ["funding_preference", "Funding preference"],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="space-y-2">
              <Label htmlFor={key}>{label}</Label>
              <Input
                id={key}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                required={["nationality", "highest_degree", "target_degree"].includes(key)}
              />
            </div>
          ))}
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="fields">Fields of interest (comma-separated)</Label>
            <Input
              id="fields"
              value={form.fields}
              onChange={(e) => setForm({ ...form, fields: e.target.value })}
              required
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="preferred_countries">Preferred countries (optional)</Label>
            <Input
              id="preferred_countries"
              value={form.preferred_countries}
              onChange={(e) => setForm({ ...form, preferred_countries: e.target.value })}
            />
          </div>
          {error && <p className="text-sm text-danger sm:col-span-2">{error}</p>}
          <div className="sm:col-span-2">
            <Button disabled={loading}>{loading ? "Saving…" : "Save and open dashboard"}</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

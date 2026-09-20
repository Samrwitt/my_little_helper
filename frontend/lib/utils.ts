import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | null) {
  if (!value) return "Not specified";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function eligibilityLabel(status?: string | null) {
  if (!status) return "Not evaluated";
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

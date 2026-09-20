export type User = {
  id: string;
  email: string;
  full_name?: string | null;
  onboarding_completed: boolean;
};

export type Profile = {
  id: string;
  user_id: string;
  nationality?: string | null;
  country_of_residence?: string | null;
  highest_degree?: string | null;
  target_degree?: string | null;
  fields: string[];
  graduation_year?: number | null;
  gpa?: number | null;
  english_tests: { ielts?: number | null; toefl?: number | null };
  work_experience_years?: number | null;
  preferred_countries: string[];
  funding_preference?: string | null;
  age?: number | null;
};

export type Scholarship = {
  id: string;
  name: string;
  provider?: string | null;
  country?: string | null;
  host_institution?: string | null;
  degree_levels: string[];
  fields_of_study: string[];
  funding_type: string;
  tuition_coverage?: boolean | null;
  stipend?: string | null;
  travel_coverage?: boolean | null;
  insurance_coverage?: boolean | null;
  accommodation_coverage?: boolean | null;
  application_deadline?: string | null;
  days_remaining?: number | null;
  verification_status: string;
  source_reliability: number;
  eligibility_status?: string | null;
  application_status?: string | null;
  description?: string | null;
  official_url?: string | null;
  eligible_nationalities?: string[];
  application_open_date?: string | null;
  minimum_gpa?: number | null;
  required_degree?: string | null;
  language_requirements?: string | null;
  age_requirement?: string | null;
  application_process?: string | null;
  fact_statuses?: Record<string, string>;
  sources?: Array<{
    id: string;
    url: string;
    title?: string | null;
    trust_score: number;
    is_official: boolean;
  }>;
  documents?: Array<{ id: string; name: string; is_required: boolean; fact_status: string }>;
  requirements?: Array<{ id: string; category: string; description: string; fact_status: string }>;
  changes?: Array<{
    id: string;
    change_type: string;
    field_name: string;
    previous_value?: string | null;
    new_value?: string | null;
    summary?: string | null;
    created_at: string;
  }>;
  match?: Match | null;
};

export type Match = {
  id: string;
  scholarship_id: string;
  status: string;
  matched_requirements: string[];
  missing_requirements: string[];
  failed_requirements: string[];
  unknown_requirements: string[];
  reasoning_summary?: string | null;
  confidence: number;
  evaluated_at: string;
  scholarship?: Scholarship | null;
};

export type Application = {
  id: string;
  scholarship_id: string;
  status: string;
  readiness_percent: number;
  notes?: string | null;
  documents: Array<{ id: string; name: string; is_complete: boolean; notes?: string | null }>;
  scholarship?: Scholarship | null;
};

export type Dashboard = {
  stats: {
    matched_scholarships: number;
    applications_in_progress: number;
    deadlines_this_month: number;
    applications_submitted: number;
  };
  upcoming_deadlines: Array<{
    scholarship_id: string;
    name: string;
    deadline?: string | null;
    days_remaining?: number | null;
    eligibility_status?: string | null;
    funding: Record<string, unknown>;
    missing_requirements: string[];
    application_status?: string | null;
  }>;
  recent_notifications: Array<{
    id: string;
    title: string;
    body: string;
    is_read: boolean;
    created_at: string;
  }>;
};

export type Notification = {
  id: string;
  channel: string;
  title: string;
  body: string;
  link?: string | null;
  is_read: boolean;
  created_at: string;
};

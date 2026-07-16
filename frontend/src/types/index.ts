export type Role =
  | "customer"
  | "surveyor"
  | "insurance_officer"
  | "repair_workshop"
  | "fraud_analyst"
  | "admin"
  | "super_admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: Role;
  is_active: boolean;
  is_verified: boolean;
  mfa_enabled: boolean;
  created_at: string;
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Vehicle {
  id: string;
  owner_id: string;
  vin: string;
  registration_number: string;
  make: string;
  model: string;
  year: number;
  color?: string | null;
  body_type?: string | null;
  odometer_km?: number | null;
  created_at: string;
}

export interface ClaimImage {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  width?: number | null;
  height?: number | null;
  angle_label?: string | null;
  virus_scan_status: string;
  created_at: string;
}

export interface DamageDetection {
  id: string;
  model_version: string;
  parts: any[];
  damages: any[];
  severity: string;
  damage_area_pct: number;
  confidence: number;
  explanation: Record<string, any>;
  created_at: string;
}

export interface CostEstimate {
  id: string;
  currency: string;
  parts_total: number;
  labour_total: number;
  painting_total: number;
  taxes_total: number;
  grand_total: number;
  repair_days: number;
  line_items: any[];
  invoice_json: Record<string, any>;
  explanation: Record<string, any>;
  created_at: string;
}

export interface FraudSignal {
  id: string;
  signal_type: string;
  severity: string;
  weight: number;
  message: string;
  evidence: Record<string, any>;
}

export interface FraudAssessment {
  id: string;
  risk_score: number;
  risk_level: string;
  summary: string;
  explanation: Record<string, any>;
  model_version: string;
  signals: FraudSignal[];
  created_at: string;
}

export interface Claim {
  id: string;
  claim_number: string;
  customer_id: string;
  vehicle_id: string;
  policy_id?: string | null;
  assigned_surveyor_id?: string | null;
  status: string;
  incident_date?: string | null;
  incident_location?: string | null;
  description?: string | null;
  severity?: string | null;
  fraud_score?: number | null;
  estimated_cost?: number | null;
  approved_amount?: number | null;
  surveyor_notes?: string | null;
  rejection_reason?: string | null;
  warranty_valid?: boolean | null;
  submitted_at?: string | null;
  created_at: string;
  updated_at: string;
  images: ClaimImage[];
  detections: DamageDetection[];
  cost_estimates: CostEstimate[];
  fraud_assessments: FraudAssessment[];
}

export interface DashboardStats {
  total_claims: number;
  pending_claims: number;
  approved_claims: number;
  rejected_claims: number;
  fraud_cases: number;
  average_claim_cost: number;
  average_processing_hours: number;
  revenue: number;
  claims_by_status: Record<string, number>;
  severity_distribution: Record<string, number>;
  brand_distribution: Record<string, number>;
  monthly_claims: { month: string; count: number }[];
  fraud_trend: { month: string; count: number }[];
}

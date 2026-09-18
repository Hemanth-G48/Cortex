// SyllabusAI material types.
// Extracted from services/api.ts (F8 split).

// ----- SyllabusAI materials -----
export interface Material {
  id: number;
  unit_id: number;
  title: string;
  description: string | null;
  file_type: string;
  file_url: string;
  file_size: number;
  original_file_name: string;
  view_count: number;
  download_count: number;
  is_active: boolean;
  extracted_text: string | null;
  created_at: string;
}

export interface MaterialListResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

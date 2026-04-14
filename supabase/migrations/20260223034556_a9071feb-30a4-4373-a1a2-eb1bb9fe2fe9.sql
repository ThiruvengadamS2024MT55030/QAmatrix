
-- Defect data uploaded by DVX, SCA, YARD teams
CREATE TABLE public.defect_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL CHECK (source IN ('DVX', 'SCA', 'YARD')),
  defect_code TEXT NOT NULL DEFAULT '',
  defect_location_code TEXT NOT NULL DEFAULT '',
  defect_description_details TEXT NOT NULL DEFAULT '',
  uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

ALTER TABLE public.defect_data ENABLE ROW LEVEL SECURITY;

-- Public read/write since no auth is set up yet
CREATE POLICY "Allow public read defect_data"
  ON public.defect_data FOR SELECT
  USING (true);

CREATE POLICY "Allow public insert defect_data"
  ON public.defect_data FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Allow public delete defect_data"
  ON public.defect_data FOR DELETE
  USING (true);

-- QA Matrix entries table
CREATE TABLE public.qa_matrix_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  s_no INTEGER NOT NULL,
  source TEXT NOT NULL DEFAULT '',
  operation_station TEXT NOT NULL DEFAULT '',
  designation TEXT NOT NULL DEFAULT '',
  concern TEXT NOT NULL DEFAULT '',
  defect_rating INTEGER NOT NULL DEFAULT 1,
  defect_code TEXT NOT NULL DEFAULT '',
  defect_location_code TEXT NOT NULL DEFAULT '',
  recurrence INTEGER NOT NULL DEFAULT 0,
  weekly_recurrence JSONB NOT NULL DEFAULT '[]',
  recurrence_count_plus_defect INTEGER NOT NULL DEFAULT 0,
  trim JSONB NOT NULL DEFAULT '{}',
  chassis JSONB NOT NULL DEFAULT '{}',
  final JSONB NOT NULL DEFAULT '{}',
  q_control JSONB NOT NULL DEFAULT '{}',
  q_control_detail JSONB NOT NULL DEFAULT '{}',
  control_rating JSONB NOT NULL DEFAULT '{}',
  guaranteed_quality JSONB NOT NULL DEFAULT '{}',
  workstation_status TEXT NOT NULL DEFAULT 'NG',
  mfg_status TEXT NOT NULL DEFAULT 'NG',
  plant_status TEXT NOT NULL DEFAULT 'NG',
  mfg_action TEXT NOT NULL DEFAULT '',
  resp TEXT NOT NULL DEFAULT '',
  target TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

ALTER TABLE public.qa_matrix_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read qa_matrix"
  ON public.qa_matrix_entries FOR SELECT
  USING (true);

CREATE POLICY "Allow public insert qa_matrix"
  ON public.qa_matrix_entries FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Allow public update qa_matrix"
  ON public.qa_matrix_entries FOR UPDATE
  USING (true);

CREATE POLICY "Allow public delete qa_matrix"
  ON public.qa_matrix_entries FOR DELETE
  USING (true);

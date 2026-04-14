
-- Create final_defect table for filtered/deduplicated defect data
CREATE TABLE public.final_defect (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  defect_code TEXT NOT NULL DEFAULT '',
  defect_location_code TEXT NOT NULL DEFAULT '',
  defect_description_details TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.final_defect ENABLE ROW LEVEL SECURITY;

-- Public access policies (no auth in this app)
CREATE POLICY "Allow public read final_defect" ON public.final_defect FOR SELECT USING (true);
CREATE POLICY "Allow public insert final_defect" ON public.final_defect FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public delete final_defect" ON public.final_defect FOR DELETE USING (true);
CREATE POLICY "Allow public update final_defect" ON public.final_defect FOR UPDATE USING (true);

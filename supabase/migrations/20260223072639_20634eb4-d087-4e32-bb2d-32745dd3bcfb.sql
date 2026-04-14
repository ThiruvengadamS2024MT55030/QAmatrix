
-- Add unique constraint on s_no for upsert support
ALTER TABLE public.qa_matrix_entries ADD CONSTRAINT qa_matrix_entries_s_no_unique UNIQUE (s_no);

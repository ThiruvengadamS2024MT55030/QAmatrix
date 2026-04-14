import { supabase } from "@/integrations/supabase/client";
import { DVXEntry } from "@/types/dvxReport";
import { QAMatrixEntry } from "@/types/qaMatrix";

interface AIMatch {
  defectIndex: number;
  matchedSNo: number | null;
  confidence: number;
  reason: string;
}

interface AIMatchResult {
  matches: AIMatch[];
}

/**
 * Use AI agent to semantically match DVX defects with QA matrix concerns.
 * Sends defects in batches to avoid token limits.
 */
export async function aiMatchDefects(
  dvxEntries: DVXEntry[],
  qaData: QAMatrixEntry[]
): Promise<AIMatchResult> {
  const concerns = qaData.map((q) => ({
    sNo: q.sNo,
    concern: q.concern,
    operationStation: q.operationStation,
    designation: q.designation,
  }));

  const BATCH_SIZE = 200;
  
  // Build all batch requests
  const batchPromises: Promise<AIMatch[]>[] = [];
  
  for (let i = 0; i < dvxEntries.length; i += BATCH_SIZE) {
    const batch = dvxEntries.slice(i, i + BATCH_SIZE);
    const batchStart = i;
    const defects = batch.map((d, idx) => ({
      index: batchStart + idx,
      locationDetails: d.locationDetails,
      defectDescription: d.defectDescription,
      defectDescriptionDetails: d.defectDescriptionDetails,
      gravity: d.gravity,
      quantity: d.quantity,
    }));

    // Fire all batches in parallel
    batchPromises.push(
      supabase.functions.invoke("match-defects", {
        body: { defects, concerns },
      }).then(({ data, error }) => {
        if (error) {
          console.error("AI matching error for batch:", error);
          return batch.map((_, idx) => ({
            defectIndex: batchStart + idx,
            matchedSNo: null,
            confidence: 0,
            reason: "AI matching failed",
          }));
        }
        if (data?.matches) return data.matches as AIMatch[];
        if (data?.error) {
          console.error("AI matching returned error:", data.error);
          return batch.map((_, idx) => ({
            defectIndex: batchStart + idx,
            matchedSNo: null,
            confidence: 0,
            reason: data.error,
          }));
        }
        return [] as AIMatch[];
      })
    );
  }

  const batchResults = await Promise.all(batchPromises);
  const allMatches = batchResults.flat();

  return { matches: allMatches };
}

import * as XLSX from "xlsx";

export function isGoogleSheetsUrl(url: string): boolean {
  return url.includes("docs.google.com/spreadsheets");
}

/**
 * Fetches an XLSX workbook via our backend edge function (avoids CORS issues).
 */
export async function fetchWorkbookFromUrl(url: string): Promise<XLSX.WorkBook> {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error("Backend not configured");
  }

  const response = await fetch(
    `${supabaseUrl}/functions/v1/fetch-spreadsheet`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": supabaseKey,
        "Authorization": `Bearer ${supabaseKey}`,
      },
      body: JSON.stringify({ url }),
    }
  );

  if (!response.ok) {
    // Try to parse error JSON
    let errMsg = `Failed to fetch spreadsheet (${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson?.error) errMsg = errJson.error;
    } catch { /* ignore */ }
    throw new Error(errMsg);
  }

  const arrayBuffer = await response.arrayBuffer();
  return XLSX.read(arrayBuffer, { type: "array" });
}

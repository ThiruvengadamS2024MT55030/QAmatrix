import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

interface DVXDefect {
  index: number;
  locationDetails: string;
  defectDescription: string;
  defectDescriptionDetails: string;
  gravity: string;
  quantity: number;
}

interface QAConcern {
  sNo: number;
  concern: string;
  operationStation: string;
  designation: string;
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) throw new Error("LOVABLE_API_KEY is not configured");

    const { defects, concerns } = (await req.json()) as {
      defects: DVXDefect[];
      concerns: QAConcern[];
    };

    if (!defects?.length || !concerns?.length) {
      return new Response(
        JSON.stringify({ matches: defects?.map(() => null) || [] }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Build a concise representation of QA concerns for the AI
    const concernsList = concerns
      .map((c) => `[${c.sNo}] "${c.concern}" (station: ${c.operationStation}, area: ${c.designation})`)
      .join("\n");

    // Build defects list
    const defectsList = defects
      .map(
        (d) =>
          `[${d.index}] Location: "${d.locationDetails}" | Defect: "${d.defectDescription}" | Details: "${d.defectDescriptionDetails}" | Gravity: ${d.gravity}`
      )
      .join("\n");

    const systemPrompt = `You are an automotive quality assurance expert. Your task is to match defect reports from vehicle inspections to known QA concerns in a quality matrix.

You must understand the SEMANTIC MEANING of each defect description and match it to the most relevant QA concern based on:
- What the actual problem is (e.g., a scratch, a loose bolt, a missing part)
- The location/area of the defect
- The type of component involved
- Manufacturing process context

Do NOT rely on simple keyword matching. Use your understanding of automotive manufacturing defects to find the best semantic match.

If a defect clearly does not match any concern, return null for that defect. It's better to leave something unmatched than to pair it incorrectly.`;

    const userPrompt = `Here are the QA Matrix concerns:
${concernsList}

Here are the defects to match:
${defectsList}

For each defect, find the best matching QA concern based on semantic understanding of the defect and concern descriptions. Return your answer using the tool provided.`;

    const response = await fetch(
      "https://ai.gateway.lovable.dev/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${LOVABLE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "google/gemini-3-flash-preview",
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt },
          ],
          tools: [
            {
              type: "function",
              function: {
                name: "submit_matches",
                description:
                  "Submit the matching results for all defects. Each match contains the defect index and the matched QA concern sNo, or null if no good match exists.",
                parameters: {
                  type: "object",
                  properties: {
                    matches: {
                      type: "array",
                      items: {
                        type: "object",
                        properties: {
                          defectIndex: {
                            type: "number",
                            description: "The index of the defect",
                          },
                          matchedSNo: {
                            type: ["number", "null"],
                            description:
                              "The sNo of the matched QA concern, or null if no match",
                          },
                          confidence: {
                            type: "number",
                            description:
                              "Confidence score 0-1 of the match quality",
                          },
                          reason: {
                            type: "string",
                            description:
                              "Brief reason for the match or why unmatched",
                          },
                        },
                        required: [
                          "defectIndex",
                          "matchedSNo",
                          "confidence",
                          "reason",
                        ],
                        additionalProperties: false,
                      },
                    },
                  },
                  required: ["matches"],
                  additionalProperties: false,
                },
              },
            },
          ],
          tool_choice: {
            type: "function",
            function: { name: "submit_matches" },
          },
        }),
      }
    );

    if (!response.ok) {
      if (response.status === 429) {
        return new Response(
          JSON.stringify({ error: "Rate limit exceeded. Please try again shortly." }),
          { status: 429, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      if (response.status === 402) {
        return new Response(
          JSON.stringify({ error: "AI usage credits depleted. Please add credits." }),
          { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
      const errorText = await response.text();
      console.error("AI gateway error:", response.status, errorText);
      throw new Error(`AI gateway error: ${response.status}`);
    }

    const aiResult = await response.json();
    const toolCall = aiResult.choices?.[0]?.message?.tool_calls?.[0];

    if (!toolCall?.function?.arguments) {
      throw new Error("No tool call response from AI");
    }

    const parsed = JSON.parse(toolCall.function.arguments);

    return new Response(JSON.stringify(parsed), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("match-defects error:", e);
    return new Response(
      JSON.stringify({
        error: e instanceof Error ? e.message : "Unknown error",
      }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});

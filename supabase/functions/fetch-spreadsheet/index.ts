const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Full browser-like headers
const BROWSER_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
  "Accept-Language": "en-US,en;q=0.9",
  "Connection": "keep-alive",
  "Upgrade-Insecure-Requests": "1",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { url } = await req.json();
    if (!url) {
      return new Response(JSON.stringify({ error: "URL is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ── Google Sheets ──────────────────────────────────────────────────────────
    const sheetsMatch = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
    if (sheetsMatch) {
      const id = sheetsMatch[1];
      const gidMatch = url.match(/[#&?]gid=(\d+)/);
      const gid = gidMatch ? gidMatch[1] : null;
      const exportUrl = `https://docs.google.com/spreadsheets/d/${id}/export?format=xlsx${gid ? `&gid=${gid}` : ""}`;
      console.log("Google Sheets → fetching:", exportUrl);
      return await proxyFetch(exportUrl);
    }

    // ── OneDrive / SharePoint ──────────────────────────────────────────────────
    if (
      url.includes("1drv.ms") ||
      url.includes("onedrive.live.com") ||
      url.includes("sharepoint.com")
    ) {
      return await handleMicrosoftLink(url);
    }

    // ── Generic URL ────────────────────────────────────────────────────────────
    return await proxyFetch(url);

  } catch (err) {
    console.error("Error:", err);
    return new Response(
      JSON.stringify({ error: err instanceof Error ? err.message : "Unknown error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

/**
 * Handles all Microsoft sharing links (1drv.ms, onedrive.live.com, sharepoint.com).
 *
 * Strategy order:
 *  1. Microsoft Graph API shared-item content endpoint (handles SPO-migrated files)
 *  2. Follow ALL redirects like a browser → return file if non-HTML received
 *  3. Extract resid + e from resolved URL → build direct download URL
 *  4. Append &download=1 to the resolved viewer URL
 */
async function handleMicrosoftLink(url: string): Promise<Response> {
  console.log("Microsoft link:", url);

  // ── Strategy 1: Microsoft Graph API ─────────────────────────────────────────
  // Works for "Anyone with the link" shared files, including SPO-migrated ones.
  // Endpoint: GET /shares/u!{base64url-encoded-sharing-url}/driveItem/content
  try {
    const encoded = btoa(url).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    const graphUrl = `https://graph.microsoft.com/v1.0/shares/u!${encoded}/driveItem/content`;
    console.log("Strategy 1 – Graph API:", graphUrl);

    const r = await fetch(graphUrl, { redirect: "follow", headers: BROWSER_HEADERS });
    const ct = r.headers.get("content-type") || "";
    console.log("Graph API response:", r.status, ct, "finalUrl:", r.url);

    if (r.ok && !ct.includes("text/html")) {
      const buf = await r.arrayBuffer();
      return fileResponse(buf, ct);
    }
  } catch (e) {
    console.error("Graph API error:", e);
  }

  // ── Strategy 2: Follow ALL redirects like a browser ─────────────────────────
  let resolvedUrl = url;
  let resolvedCt = "";
  try {
    const followed = await fetch(url, { redirect: "follow", headers: BROWSER_HEADERS });
    resolvedUrl = followed.url;
    resolvedCt = followed.headers.get("content-type") || "";
    console.log("Strategy 2 – followed to:", resolvedUrl, "ct:", resolvedCt);

    // Got the file directly
    if (followed.ok && !resolvedCt.includes("text/html")) {
      const buf = await followed.arrayBuffer();
      return fileResponse(buf, resolvedCt);
    }

    // Ended up on a login page
    if (
      resolvedUrl.includes("login.live.com") ||
      resolvedUrl.includes("login.microsoftonline.com")
    ) {
      return jsonError(
        403,
        'The file requires sign-in. In OneDrive, set sharing to "Anyone with the link" ' +
        "with no sign-in required, then paste the link again."
      );
    }
  } catch (e) {
    console.error("Redirect follow error:", e);
  }

  // ── Strategy 3: Extract resid + e → build direct download URL ────────────────
  // The resolved onedrive.live.com viewer URL contains:
  //   ?resid=USERID!sXXXX&e=AUTHKEY&migratedtospo=true&...
  // Direct download: onedrive.live.com/download?resid=RESID&authkey=!AUTHKEY
  try {
    const parsed = new URL(resolvedUrl);
    const resid = parsed.searchParams.get("resid");
    const eToken = parsed.searchParams.get("e");

    if (resid && eToken) {
      // Try with ! prefix (standard OneDrive authkey format)
      for (const prefix of ["!", ""]) {
        const dlUrl = `https://onedrive.live.com/download?resid=${encodeURIComponent(resid)}&authkey=${prefix}${eToken}`;
        console.log(`Strategy 3 – download URL (authkey ${prefix || "no"} prefix):`, dlUrl);
        const r = await fetch(dlUrl, { redirect: "follow", headers: BROWSER_HEADERS });
        const ct = r.headers.get("content-type") || "";
        if (r.ok && !ct.includes("text/html")) {
          const buf = await r.arrayBuffer();
          return fileResponse(buf, ct);
        }
        console.log(`Strategy 3 failed (${prefix || "no"} prefix):`, r.status, ct);
      }

      // Strategy 3b: For SPO-migrated files, try the SharePoint download URL.
      // The resid format "USERID!sUNIQUEID" maps to a SharePoint UniqueId (UUID).
      // Tenant domain pattern: USERID-my.sharepoint.com/personal/USERID
      const spoMatch = resid.match(/^([A-Fa-f0-9]+)!s([A-Fa-f0-9]+)$/i);
      if (spoMatch) {
        const userId = spoMatch[1].toLowerCase();
        const rawId = spoMatch[2];
        // Format as UUID: 8-4-4-4-12
        const uuid = `${rawId.slice(0,8)}-${rawId.slice(8,12)}-${rawId.slice(12,16)}-${rawId.slice(16,20)}-${rawId.slice(20)}`;
        const spoUrl =
          `https://${userId}-my.sharepoint.com/personal/${userId}/_layouts/15/download.aspx` +
          `?UniqueId=${uuid}&e=${eToken}`;
        console.log("Strategy 3b – SPO download URL:", spoUrl);
        const r = await fetch(spoUrl, { redirect: "follow", headers: BROWSER_HEADERS });
        const ct = r.headers.get("content-type") || "";
        if (r.ok && !ct.includes("text/html")) {
          const buf = await r.arrayBuffer();
          return fileResponse(buf, ct);
        }
        console.log("Strategy 3b failed:", r.status, ct);
      }
    }
  } catch (e) {
    console.error("resid extraction error:", e);
  }

  // ── Strategy 4: Append download=1 to the resolved viewer URL ─────────────────
  const sep = resolvedUrl.includes("?") ? "&" : "?";
  const downloadUrl = `${resolvedUrl}${sep}download=1`;
  console.log("Strategy 4 – download=1:", downloadUrl);
  const r4 = await fetch(downloadUrl, { redirect: "follow", headers: BROWSER_HEADERS });
  const ct4 = r4.headers.get("content-type") || "";
  if (r4.ok && !ct4.includes("text/html")) {
    const buf = await r4.arrayBuffer();
    return fileResponse(buf, ct4);
  }

  console.error("All strategies failed. Last status:", r4.status, ct4);
  return jsonError(
    502,
    "Could not download the OneDrive/SharePoint file. " +
    'Make sure the file is shared as "Anyone with the link" with no sign-in required.'
  );
}

/** Proxy a URL and return its binary response. */
async function proxyFetch(fetchUrl: string): Promise<Response> {
  const response = await fetch(fetchUrl, { headers: BROWSER_HEADERS, redirect: "follow" });
  if (!response.ok) {
    console.error("Fetch failed:", response.status, fetchUrl);
    return jsonError(502, `Failed to fetch: ${response.status} ${response.statusText}`);
  }
  const ct = response.headers.get("content-type") || "application/octet-stream";
  const buf = await response.arrayBuffer();
  return fileResponse(buf, ct);
}

function fileResponse(buf: ArrayBuffer, ct: string): Response {
  return new Response(buf, {
    status: 200,
    headers: {
      ...corsHeaders,
      "Content-Type": ct || "application/octet-stream",
      "Content-Length": buf.byteLength.toString(),
    },
  });
}

function jsonError(status: number, message: string): Response {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

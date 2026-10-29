// Edge Function: bill-documents  (optional; the Supabase connector has no Storage upload tool)
// POST /upload   body: { file_name, mime_type, base64, doc_type?, notes?, ocr_text?, link?: { one_off_bill_id | bill_instance_id | transaction_id | income_event_id } }
//                -> uploads to bucket 'bill-documents' at <yyyy>/<mm>/<uuid>-<file>, inserts public.documents, returns the row
//                   (if the same file (sha256) already exists, returns the existing row instead)
// POST /signed-url body: { document_id, expires_in? } -> { url } (short-lived signed URL for viewing)
// Auth: header x-upload-secret must equal the function secret UPLOAD_SECRET (set with `supabase secrets set`).
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are provided to Edge Functions by Supabase; never copy them anywhere else.
import { createClient } from "npm:@supabase/supabase-js@2";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const BUCKET = "bill-documents";
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { "content-type": "application/json" } });

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  if (req.headers.get("x-upload-secret") !== Deno.env.get("UPLOAD_SECRET")) return json({ error: "unauthorized" }, 401);
  const route = new URL(req.url).pathname.split("/").pop();
  const body = await req.json();

  if (route === "signed-url") {
    const { data: doc } = await db.from("documents").select("storage_path").eq("id", body.document_id).single();
    if (!doc) return json({ error: "not found" }, 404);
    const { data, error } = await db.storage.from(BUCKET).createSignedUrl(doc.storage_path, body.expires_in ?? 600);
    return error ? json({ error: error.message }, 500) : json({ url: data.signedUrl });
  }

  if (route === "upload") {
    const bytes = Uint8Array.from(atob(body.base64), (c) => c.charCodeAt(0));
    const sha256 = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((b) => b.toString(16).padStart(2, "0")).join("");
    const { data: dup } = await db.from("documents").select("*").eq("sha256", sha256).maybeSingle();
    if (dup) return json({ duplicate: true, document: dup });
    const now = new Date();
    const safe = String(body.file_name).replace(/[^A-Za-z0-9._-]+/g, "_").slice(-80);
    const path = `${now.getUTCFullYear()}/${String(now.getUTCMonth() + 1).padStart(2, "0")}/${crypto.randomUUID()}-${safe}`;
    const up = await db.storage.from(BUCKET).upload(path, bytes, { contentType: body.mime_type, upsert: false });
    if (up.error) return json({ error: up.error.message }, 500);
    const { data, error } = await db.from("documents").insert({
      storage_path: path, file_name: body.file_name, mime_type: body.mime_type, size_bytes: bytes.length, sha256,
      doc_type: body.doc_type ?? "bill_photo", notes: body.notes ?? null, ocr_text: body.ocr_text ?? null, ...(body.link ?? {}),
    }).select().single();
    if (error) { await db.storage.from(BUCKET).remove([path]); return json({ error: error.message }, 500); }
    return json({ duplicate: false, document: data });
  }
  return json({ error: "unknown route" }, 404);
});

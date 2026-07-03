const ANTHROPIC_URL = "https://api.anthropic.com/v1/messages";
const DEFAULT_MODEL = "claude-sonnet-4-20250514";

module.exports = async function handler(req, res) {
  if (!applyCors(req, res)) {
    return;
  }

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    res.status(500).json({ error: "ANTHROPIC_API_KEY is not configured" });
    return;
  }

  let body = {};
  try {
    body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
  } catch (error) {
    res.status(400).json({ error: "Invalid JSON body" });
    return;
  }
  const question = String(body.question || "").trim();
  const contexts = Array.isArray(body.contexts) ? body.contexts.slice(0, 8) : [];

  if (!question) {
    res.status(400).json({ error: "Question is required" });
    return;
  }
  if (!contexts.length) {
    res.status(400).json({ error: "At least one context is required" });
    return;
  }

  const sourceBlock = contexts
    .map((context, index) => {
      const label = index + 1;
      const title = clean(context.sourceTitle || `Source ${label}`, 160);
      const path = clean(context.sourcePath || "", 220);
      const text = clean(context.text || "", 2400);
      return `[${label}] ${title}\n${path}\n${text}`;
    })
    .join("\n\n");

  const payload = {
    model: process.env.ANTHROPIC_MODEL || DEFAULT_MODEL,
    max_tokens: Number(process.env.ANTHROPIC_MAX_TOKENS || 1000),
    temperature: 0.2,
    system:
      "You answer iPAS AI study questions using only the supplied sources. " +
      "Write in the user's language. Cite source numbers like [1] when using facts. " +
      "If the sources are insufficient, say what is missing.",
    messages: [
      {
        role: "user",
        content: `Question:\n${question}\n\nSources:\n${sourceBlock}`,
      },
    ],
  };

  try {
    const upstream = await fetch(ANTHROPIC_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(payload),
    });
    const data = await upstream.json();
    if (!upstream.ok) {
      res.status(upstream.status).json({
        error: data?.error?.message || "Anthropic request failed",
      });
      return;
    }

    const answer = (data.content || [])
      .filter((part) => part.type === "text")
      .map((part) => part.text)
      .join("\n\n")
      .trim();

    res.status(200).json({
      answer,
      model: data.model || payload.model,
      usage: data.usage || null,
    });
  } catch (error) {
    res.status(500).json({ error: error.message || "Unexpected error" });
  }
};

function applyCors(req, res) {
  const origin = req.headers.origin || "";
  const allowed = (process.env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  if (allowed.length && origin && !allowed.includes(origin)) {
    res.status(403).json({ error: "Origin not allowed" });
    return false;
  }

  res.setHeader("access-control-allow-origin", allowed.length ? origin || allowed[0] : "*");
  res.setHeader("access-control-allow-methods", "POST, OPTIONS");
  res.setHeader("access-control-allow-headers", "content-type");
  return true;
}

function clean(value, maxLength) {
  return String(value).replace(/\s+/g, " ").trim().slice(0, maxLength);
}

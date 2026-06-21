import { useState } from "react";
import { postJson } from "../lib/api";
import Card from "./Card";

export default function CommandPanel({ onCommandResult, bare = false }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitCommand(event) {
    event.preventDefault();

    if (!text.trim()) return;

    setLoading(true);
    try {
      const result = await postJson("/api/command", { text });
      onCommandResult(result);
      setText("");
    } finally {
      setLoading(false);
    }
  }

  const form = (
    <form onSubmit={submitCommand} className="space-y-3">
      <input
        className="input-glass w-full rounded-2xl px-4 py-3 text-sm"
        placeholder='Try “add schedule date 2026-05-20 time 15:30 purpose revision priority high”'
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <button
        type="submit"
        className="btn-primary px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
        disabled={loading}
      >
        {loading ? "Sending..." : "Send Command"}
      </button>
    </form>
  );

  if (bare) return form;

  return <Card title="Ask JUNO">{form}</Card>;
}

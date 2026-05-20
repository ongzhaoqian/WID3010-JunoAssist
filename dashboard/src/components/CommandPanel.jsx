import { useState } from "react";
import { postJson } from "../lib/api";
import Card from "./Card";

export default function CommandPanel({ onCommandResult }) {
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

  return (
    <Card title="Ask JUNO">
      <form onSubmit={submitCommand} className="space-y-3">
        <input
          className="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 outline-none focus:ring-2 focus:ring-slate-400"
          placeholder='Try "Hey, John", then "Yes", or "What do I have today?"'
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button
          type="submit"
          className="rounded-xl bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Sending..." : "Send Command"}
        </button>
      </form>
    </Card>
  );
}

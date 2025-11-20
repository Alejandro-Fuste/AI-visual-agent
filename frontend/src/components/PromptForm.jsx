import { useState } from "react";

function PromptForm({ onRunStart }) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
      }

      const data = await response.json();
      onRunStart(data.run_id);
      setPrompt("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        maxWidth: "400px",
      }}
    >
      <label>
        Prompt:
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          required
        />
      </label>

      <button
        type="submit"
        disabled={loading}
        style={{
          background: "#faaa47",
          color: "#fff",
          border: "none",
          padding: "0.6rem 1rem",
          cursor: "pointer",
          borderRadius: "8px",
          fontWeight: "600",
          transition: "background 0.3s ease",
        }}
        onMouseEnter={(e) => (e.target.style.background = "#fbc46b")}
        onMouseLeave={(e) => (e.target.style.background = "#faaa47")}
      >
        {loading ? "Running..." : "Go"}
      </button>

      {error && <p style={{ color: "red" }}>⚠️ {error}</p>}
    </form>
  );
}

export default PromptForm;

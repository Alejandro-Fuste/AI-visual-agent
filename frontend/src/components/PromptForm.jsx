import { useState } from "react";
import { apiFetch } from "../api";

function PromptForm({ onRunStart }) {
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("prompt", prompt);
      if (file) formData.append("file", file);

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/run`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || response.statusText);
      }

      const data = await response.json();
      onRunStart(data.run_id);
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
          style={{ width: "100%" }}
        />
      </label>

      <label>
        Upload file (optional):
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          accept="image/*,.pdf"
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

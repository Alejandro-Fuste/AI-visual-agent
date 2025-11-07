const API_BASE = import.meta.env.VITE_API_URL;
console.log("API_BASE:", API_BASE);

// Helper function for fetch calls
export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(errText || response.statusText);
  }
  return response.json();
}

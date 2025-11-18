import { useEffect, useState } from "react";
import LeftColumn from "./components/LeftColumn";
import PromptForm from "./components/PromptForm";
import BrandHeader from "./components/BrandHeader";
import RePromptModal from "./components/RePromptModal";
import { apiFetch } from "./api";
import styles from "./App.module.css";

function App() {
  const [status, setStatus] = useState("Idle");
  const [runId, setRunId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMessage, setModalMessage] = useState("");
  const [actionResult, setActionResult] = useState(null);

  useEffect(() => {
    if (!runId) return;

    let cancelled = false;
    let intervalId;

    const pollStatus = async () => {
      try {
        const data = await apiFetch(`/api/status/${runId}`);
        if (cancelled) return;
        setLogs(data.logs || []);
        setStatus(data.status);
        if (data.result) {
          setActionResult(data.result);
        }

        if (data.pending_question && data.status === "needs_input") {
          setModalMessage(data.pending_question);
          setModalOpen(true);
        }

        if (data.status === "success" || data.status === "error") {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error(err);
        setStatus("error");
        clearInterval(intervalId);
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 2000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [runId]);

  const handleRunStart = (id) => {
    setRunId(id);
    setLogs([]);
    setStatus("Running...");
    setActionResult(null);
    setModalOpen(false);
    setModalMessage("");
  };

  const handleModalSubmit = async (userResponse) => {
    if (!userResponse || !runId) {
      setModalOpen(false);
      return;
    }
    await apiFetch("/api/reprompt", {
      method: "POST",
      body: JSON.stringify({ run_id: runId, message: userResponse }),
    });
    setModalOpen(false);
    setStatus("Running...");
  };

  return (
    <div className={styles.appContainer}>
      <BrandHeader />
      <main className={styles.mainContent}>
        <div className={styles.leftContainer}>
          <LeftColumn />
        </div>

        <div className={styles.rightContainer}>
          <div className={styles.formCard}>
            <h2 className={styles.formHeader}>Run the Visual Agent</h2>
            <PromptForm onRunStart={handleRunStart} />
            <div className={styles.statusSection}>
              <h3>Status: {status}</h3>
              <ul className={styles.logList}>
                {logs.map((log, i) => (
                  <li key={`${log.stage}-${i}`}>
                    <strong>{log.stage}</strong>: {log.message}
                  </li>
                ))}
              </ul>
            </div>
            {actionResult && (
              <div className={styles.resultSection}>
                <h3>Agent Output</h3>
                <p>{actionResult.final_message}</p>
                {actionResult.actions && actionResult.actions.length > 0 && (
                  <ol className={styles.actionList}>
                    {actionResult.actions.map((act, idx) => (
                      <li key={`action-${idx}`}>
                        <strong>{act.action}</strong>: {act.message}
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      <RePromptModal
        show={modalOpen}
        message={modalMessage}
        onSubmit={handleModalSubmit}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}

export default App;

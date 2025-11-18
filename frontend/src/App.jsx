import { useState, useEffect } from "react";
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

  useEffect(() => {
    if (!runId) return; // don't poll until a run has started
  
    let lastLogCount = 0;
    const interval = setInterval(async () => {
      try {
        const data = await apiFetch(`/api/status/${runId}`);
        setLogs(data.logs);
        setStatus(data.status);
  
        // Detect new log entries since the last poll
        if (data.logs.length > lastLogCount) {
          const newLogs = data.logs.slice(lastLogCount);
  
          // Check if any new log entry is a "reprompt"
          const repromptLog = newLogs.find((log) => log.stage === "reprompt");
          if (repromptLog) {
            console.log("🔁 LLM requested clarification:", repromptLog.message);
            setModalMessage(repromptLog.message);
            setModalOpen(true);
          }
  
          lastLogCount = data.logs.length;
        }
  
        // Stop polling when run completes
        if (data.status === "success" || data.status === "error") {
          clearInterval(interval);
        }
      } catch (err) {
        console.error("❌ Error polling status:", err);
        clearInterval(interval);
      }
    }, 1500);
  
    return () => clearInterval(interval);
  }, [runId]);
  

  // Simulate a backend re-prompt trigger (or real via LLM)
  // const triggerReprompt = async () => {
  //   const data = await apiFetch("/api/reprompt", {
  //     method: "POST",
  //     body: JSON.stringify({
  //       run_id: runId || "demo-run-id",
  //       message: "Can you clarify your last prompt?",
  //     }),
  //   });
  //   if (data.acknowledged) {
  //     setModalMessage("Can you clarify your last prompt?");
  //     setModalOpen(true);
  //   }
  // };

  const handleModalSubmit = async (userResponse) => {
    setModalOpen(false);

    if (!runId) {
      console.warn("No run ID found – skipping reprompt submission.");
      return;
    }

    try {
      const res = await apiFetch("/api/reprompt", {
        method: "POST",
        body: JSON.stringify({
          run_id: runId,
          message: userResponse,
        }),
      });

    } catch (err) {
      console.error("❌ Error sending reprompt:", err);
    }
  };


  return (
    <div className={styles.appContainer}>
      <BrandHeader />
      <main className={styles.mainContent}>
        <div className={styles.leftContainer}>
          <LeftColumn />
          {/* <button
            className={styles.modalButtonSubmit}
            onClick={triggerReprompt}
          >
            Simulate Re-Prompt
          </button> */}
        </div>

        <div className={styles.rightContainer}>
          <div className={styles.formCard}>
            <h2 className={styles.formHeader}>Run the Visual Agent</h2>
            <PromptForm onRunStart={setRunId} />
            <div className={styles.statusSection}>
              <h3>Status: {status}</h3>
              <ul className={styles.logList}>
                {logs.map((log, i) => (
                  <li key={i}>
                    <strong>{log.stage}</strong>: {log.message}
                  </li>
                ))}
              </ul>
            </div>
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

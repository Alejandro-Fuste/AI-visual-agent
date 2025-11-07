// App.jsx
import { useState } from "react";
import LeftColumn from "./components/LeftColumn";
import PromptForm from "./components/PromptForm";
import BrandHeader from "./components/BrandHeader";
import { apiFetch } from "./api";
import styles from "./App.module.css";

function App() {
  const [status, setStatus] = useState("Idle");
  const [logs, setLogs] = useState([]);

  const handleRunStart = (id) => {
    setStatus("Running...");
    pollStatus(id);
  };

  const pollStatus = async (id) => {
    const interval = setInterval(async () => {
      const data = await apiFetch(`/api/status/${id}`);
      setLogs(data.logs);
      setStatus(data.status);

      if (data.status === "success" || data.status === "error") {
        clearInterval(interval);
      }
    }, 1500);
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
                  <li key={i}>
                    <strong>{log.stage}</strong>: {log.message}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;

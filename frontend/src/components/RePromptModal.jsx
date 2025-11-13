import { useState } from "react";
import styles from "../App.module.css";

function RePromptModal({ show, message, onSubmit, onClose }) {
  const [response, setResponse] = useState("");

  if (!show) return null;

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <h2 className={styles.modalTitle}>Additional Info Needed</h2>
        <p className={styles.modalMessage}>{message}</p>

        <textarea
          placeholder="Enter your response..."
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          className={styles.modalTextarea}
        />

        <div className={styles.modalButtons}>
          <button
            className={styles.modalButtonSubmit}
            onClick={() => {
              onSubmit(response);
              setResponse("");
            }}
          >
            Submit
          </button>
          <button className={styles.modalButtonClose} onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default RePromptModal;

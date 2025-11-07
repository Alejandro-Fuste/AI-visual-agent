// src/components/LeftColumn.jsx
import styles from "../App.module.css";

function LeftColumn() {
  return (
    
    <section className={styles.leftColumn}>
      {/* <div className={styles.brandRow}>
        <img src="/logo.png" alt="Visual Agent logo" className={styles.logo} />
        <h1 className={styles.projectName}>Visual Agent</h1>
      </div> */}

      <div className={styles.introBlock}>
        <h2>Welcome to Visual Agent</h2>
        <p>
          Our AI assistant automates web form interactions based on a simple text prompt.
          Upload a screenshot or document, and watch the system take action intelligently.
        </p>
        <p className={styles.callToAction}>
          Start your test on the right to see the agent in action.
        </p>
      </div>
    </section>
  );
}

export default LeftColumn;

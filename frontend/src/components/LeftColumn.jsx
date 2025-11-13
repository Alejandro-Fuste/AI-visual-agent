// src/components/LeftColumn.jsx
import styles from "../App.module.css";

function LeftColumn() {
  return (

    <section className={styles.leftColumn}>

      <div className={styles.introBlock}>
        <h2>Welcome to Visual Agent!</h2>
        <p className={styles.reasonText}>
          Our AI agent automates web form interactions based on a simple text prompt. Upload a screenshot or document, and watch the system take action intelligently.

          Built for researchers, developers, and innovators, Visual Agent demonstrates how computer vision and language models can work together to interpret interfaces and execute real-world tasks.

          Harness the power of visual understanding and reasoning — turning static screenshots into dynamic, intelligent workflows.
        </p>
        <p className={styles.callToAction}>
          Start your test on the right to see the agent in action.
        </p>
      </div>
    </section>
  );
}

export default LeftColumn;

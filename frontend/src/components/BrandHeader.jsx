import styles from "../App.module.css";

function BrandHeader() {
  return (
    <div className={styles.brandRow}>
      <img src="/logo.png" alt="Visual Agent logo" className={styles.logo} />
      <h1 className={styles.projectName}>Visual Agent</h1>
    </div>
  );
}

export default BrandHeader;

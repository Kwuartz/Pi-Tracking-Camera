export default function ManualToggle({manualMode, onToggle}) {
  return (
    <button type="button" onClick={() => onToggle(!manualMode)}>
      {manualMode ? "Manual" : "Tracking"}
    </button>
  );
}

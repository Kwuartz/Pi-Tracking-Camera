export default function Toggle({ value, onToggle, label }) {
  return (
    <button type="button" onClick={() => onToggle(!value)}>
      {label}: {String(value)}
    </button>
  );
}

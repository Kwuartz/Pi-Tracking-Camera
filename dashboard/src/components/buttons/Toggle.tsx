interface Props {
    value: boolean;
    onToggle: (v: boolean) => void;
    label: string;
    disabled?: boolean;
}

export default function Toggle({ value, onToggle, label, disabled }: Props) {
    return (
        <div className="flex flex-col items-center">
            <span className="text-sm mb-1 text-gray-300">{label}</span>
            <button
                disabled={disabled}
                onClick={() => onToggle(!value)}
                className={`w-14 h-7 rounded-full p-1 transition ${
                    value ? "bg-gray-700" : "bg-gray-600"
                } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
            >
                <div
                    className={`w-5 h-5 bg-white rounded-full shadow transition-transform duration-300 ${
                        value ? "translate-x-7" : "translate-x-0"
                    }`}
                />
            </button>
        </div>
    );
}

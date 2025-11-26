interface Props {
    direction: string;
    setDirection: (d: string | null) => void;
}

export default function JoystickButton({ direction, setDirection }: Props) {
    return (
        <button
            onMouseDown={() => setDirection(direction)}
            onMouseUp={() => setDirection(null)}
            onMouseLeave={() => setDirection(null)}
            className="
                w-16 h-16 flex items-center justify-center
                bg-gray-700 hover:bg-gray-600
                rounded-full
                border border-gray-600
                shadow-sm
                text-lg font-semibold
                active:scale-95
                transition
            "
        >
            {direction.toUpperCase()}
        </button>
    );
}

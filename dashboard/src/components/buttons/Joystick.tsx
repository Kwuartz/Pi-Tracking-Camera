import JoystickButton from "./JoystickButton";

interface Props {
    setDirection: (d: string | null) => void;
}

export default function Joystick({ setDirection }: Props) {
    return (
        <div className="flex flex-col items-center gap-2 mt-2">
            <JoystickButton direction="up" setDirection={setDirection} />
            <div className="flex gap-2">
                <JoystickButton direction="left" setDirection={setDirection} />
                <div className="w-16 h-16 rounded-full border border-gray-600" />
                <JoystickButton direction="right" setDirection={setDirection} />
            </div>
            <JoystickButton direction="down" setDirection={setDirection} />
        </div>
    );
}

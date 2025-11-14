import JoystickButton from "./JoystickButton";

type Direction = "up" | "down" | "left" | "right"

function Joystick({manualMode, setDirection}) {
    return (
    <div>
        <JoystickButton direction="up" setDirection={setDirection} />
        <JoystickButton direction="down" setDirection={setDirection} />
        <JoystickButton direction="left" setDirection={setDirection} />
        <JoystickButton direction="right" setDirection={setDirection} />
    </div>
    );
}

export default Joystick

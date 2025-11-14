import JoystickButton from "./JoystickButton";

type Direction = "up" | "down" | "left" | "right"

function Joystick({manualMode}) {
    const handleMove = (direction: Direction) => {
        console.log("Move:", direction);
    };

    return (
    <div>
        <JoystickButton direction="up" onClick={handleMove} />
        <JoystickButton direction="down" onClick={handleMove} />
        <JoystickButton direction="left" onClick={handleMove} />
        <JoystickButton direction="right" onClick={handleMove} />
    </div>
    );
}

export default Joystick

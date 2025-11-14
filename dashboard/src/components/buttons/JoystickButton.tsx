function JoystickButton({direction, onClick}) {
    return (
    <button onClick={() => onClick(direction)}>
        {direction.toUpperCase()}
    </button>
    );
}

export default JoystickButton
function JoystickButton({direction, setDirection}) {
    return (
    <button onMouseDown={() => setDirection(direction)} onMouseUp={() => setDirection(null)} onMouseLeave={() => setDirection(null)}>
        {direction.toUpperCase()}
    </button>
    );
}

export default JoystickButton
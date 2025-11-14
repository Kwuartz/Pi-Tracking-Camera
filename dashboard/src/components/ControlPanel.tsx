import { useState, useEffect } from "react"
import Joystick from "./buttons/Joystick";
import Toggle from "./buttons/Toggle";
import ResolutionControl from "./buttons/ResolutionControl";

type Resolution = "480p" | "720p" | "1080p";

function ControlPanel() {
    const [joystickDirection, setJoystickDirection] = useState(null);

    const [currentResolution, setCurrentResolution] = useState("480p");

    const [toggles, setToggles] = useState({
        manual: false,
        fps: false,
        overlay: true,
    });
    
    const handleToggle = (key, value : boolean) => {
        setToggles(prev => ({
            ...prev,
            [key]: value,
        }));

        fetch("/api/toggle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, value }),
        }).catch(err => console.error("Failed to notify server:", err));
    };

    const handleResolution = (resolution : Resolution) => {
        setCurrentResolution(resolution);
    
        fetch("/api/resolution", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resolution }),
        }).catch(err => console.error("Failed to notify server:", err));
    };

    useEffect(() => {
        if (!joystickDirection) return;
      
        const interval = setInterval(() => {
            fetch("/api/joystick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ direction: joystickDirection }),
            }).catch(err => console.error("Failed to send joystick:", err));
        }, 100);
      
        return () => clearInterval(interval);
    }, [joystickDirection]);

    return (
        <div>
            <ResolutionControl 
                current={currentResolution}
                onClick={handleResolution}
            />

            <Toggle
                value={toggles.manual}
                onToggle={(value) => handleToggle("manual", value)}
                label="Manual Mode"
            />

            <Toggle
                value={toggles.fps}
                onToggle={(value) => handleToggle("fps", value)}
                label="Show FPS"
            />

            <Toggle
                value={toggles.overlay}
                onToggle={(value) => handleToggle("overlay", value)}
                label="Show Overlay"
            />

            <Joystick 
                manualMode={toggles.manualMode}
                setDirection={setJoystickDirection}
            />
        </div>
    );
}

export default ControlPanel
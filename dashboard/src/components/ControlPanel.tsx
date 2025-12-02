import { useState, useEffect } from "react"
import Joystick from "./buttons/Joystick";
import Toggle from "./buttons/Toggle";
import ResolutionControl from "./buttons/ResolutionControl";

type Resolution = "720p" | "900p" | "1080p";

function ControlPanel( {source} ) {
    const [joystickDirection, setJoystickDirection] = useState(null);

    const [currentResolution, setCurrentResolution] = useState("1080p");

    const [toggles, setToggles] = useState({
        manual: false,
        fps: true,
        overlay: true,
    });
    
    const handleToggle = (key, value : boolean) => {
        setToggles(prev => ({
            ...prev,
            [key]: value,
        }));

        fetch(`${source}/api/toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, value }),
        }).catch(err => console.error("Failed to notify server:", err));
    };

    const handleResolution = (resolution : Resolution) => {
        setCurrentResolution(resolution);
    
        fetch(`${source}/api/resolution`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resolution }),
        }).catch(err => console.error("Failed to notify server:", err));
    };

    useEffect(() => {
        if (!joystickDirection) return;
      
        const interval = setInterval(() => {
            fetch(`${source}/api/joystick`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ direction: joystickDirection }),
            }).catch(err => console.error("Failed to send joystick:", err));
        }, 100);
      
        return () => clearInterval(interval);
    }, [joystickDirection]);

    return (
        <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-4 max-h-screen">
            <ResolutionControl 
                current={currentResolution}
                onClick={handleResolution}
            />

            <div className="flex gap-2">
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
            </div>

            {toggles.manual && (
                <Joystick 
                    manualMode={toggles.manualMode}
                    setDirection={setJoystickDirection}
                />
            )}
        </div>
    );
}

export default ControlPanel
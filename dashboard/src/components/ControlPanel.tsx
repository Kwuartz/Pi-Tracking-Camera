import { useState } from "react"
import Joystick from "./buttons/Joystick";
import ManualToggle from "./buttons/ManualToggle";
import ResolutionControl from "./buttons/ResolutionControl";

function ControlPanel() {
    const [manualMode, setManualMode] = useState(false);
    const [currentResolution, setCurrentResolution] = useState("480p");

    return (
        <div>
            <ResolutionControl 
                current={currentResolution}
                onClick={setCurrentResolution}
            />

            <ManualToggle 
                manualMode={manualMode}
                onToggle={setManualMode}
            />

            <Joystick 
                manualMode={manualMode}
            />
        </div>
    );
}

export default ControlPanel
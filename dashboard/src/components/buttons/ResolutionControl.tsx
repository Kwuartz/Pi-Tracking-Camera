type Resolution = "480p" | "720p" | "1080p";

function ResolutionControl({current, onClick}) {
    const resolutions: Resolution[] = ["480p", "720p", "1080p"];
    
    const handleClick = () => {
        const currentIndex = resolutions.indexOf(current);
        const nextIndex = (currentIndex + 1) % resolutions.length;
        const nextResolution = resolutions[nextIndex];
        onClick(nextResolution);
    };

    return <button onClick={handleClick}>Resolution: {current}</button>;
}

export default ResolutionControl
import VideoFeed from "./components/VideoFeed";
import ControlPanel from "./components/ControlPanel";

export default function App() {
    const serverSource = "http://192.168.1.173:8000"

    return (
        <div className="min-h-screen max-h-screen w-screen bg-black text-white flex flex-col lg:flex-row p-2 gap-2">
            <VideoFeed source={serverSource} />
            <ControlPanel source={serverSource} />
        </div>
    );
}

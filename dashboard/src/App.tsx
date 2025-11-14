import Title from "./components/Title";
import VideoFeed from "./components/VideoFeed";
import ControlPanel from "./components/ControlPanel";

function App() {
  const videoSource = "/video";

  return (
  <div>
    <Title />
    <VideoFeed videoSource={"http://192.168.1.173:8000/video"} />
    <ControlPanel />
  </div>
  );
}

export default App
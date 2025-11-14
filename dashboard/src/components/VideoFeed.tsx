function VideoFeed({ videoSource }) {
    return (
      <img
        src={videoSource}
        style={{
          width: "70vw",          // 70% of the viewport width
          height: "auto",         // maintain aspect ratio
          objectFit: "contain",   // prevent cropping
          display: "block",
          margin: "0 auto",       // center horizontally
        }}
        alt="Video Feed"
      />
    );
  }
  
  export default VideoFeed;
  
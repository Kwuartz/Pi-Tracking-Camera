import { useState } from "react";

export default function VideoFeed({ source }) {
    return (
        <div className="flex-1 min-h-full max-h-screen bg-gray-900 rounded-lg border border-gray-700 flex items-center justify-center overflow-hidden text-gray-500">
            <img
                src={`${source}/video`}
                alt="Video Feed"
                className="w-full h-full object-contain"
            />
        </div>
    );
}

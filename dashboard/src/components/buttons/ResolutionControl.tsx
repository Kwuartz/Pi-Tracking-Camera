type Resolution = "720p" | "900p" | "1080p";

interface Props {
    current: string;
    onClick: (res: Resolution) => void;
}

export default function ResolutionControl({ current, onClick }: Props) {
    const resolutions: Resolution[] = ["720p", "900p", "1080p"];
    
    return (
        <div className="flex flex-col w-full">
            <span className="text-sm text-gray-300 mb-1">Resolution</span>
            <div className="flex gap-2 w-full">
                {resolutions.map((res) => (
                    <button
                        key={res}
                        onClick={() => onClick(res)}
                        className={`flex-1 px-2 py-1 rounded-lg text-center text-sm font-medium ${
                            res === current ? "bg-gray-700" : "bg-gray-600"
                        }`}
                    >
                        {res}
                    </button>
                ))}
            </div>
        </div>
    );
}

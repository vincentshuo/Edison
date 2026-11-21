import { useEffect, useRef, useState } from "react";
import { YouTubeIcon } from "./YouTubeIcon";
import { Icon } from "./Icon";
import { ChannelDirectory } from "./ChannelDirectory";

type Surface = "youtube" | "curriculum" | "curriculum-archive";

export function Sidebar({
  surface,
  youtubeChannel,
  onOpenYouTube,
  onSelectChannel,
  onOpenCurriculum,
}: {
  surface: Surface;
  youtubeChannel: string;
  onOpenYouTube: () => void;
  onSelectChannel: (id: string) => void;
  onOpenCurriculum: () => void;
}) {
  const [directory, setDirectory] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const switchButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const node = sidebar.current;
    if (!node) return;
    let distance = 0;
    let last = 0;
    let direction = 0;
    let flipped = false;
    const wheel = (event: WheelEvent) => {
      const now = performance.now();
      if (event.ctrlKey || Math.abs(event.deltaX) <= Math.abs(event.deltaY) * 1.4) return;
      event.preventDefault();
      const nextDirection = Math.sign(event.deltaX);
      if (direction !== nextDirection || now - last > 180) {
        distance = 0;
        flipped = false;
      }
      direction = nextDirection;
      last = now;
      if (flipped) return;
      distance += event.deltaX * (event.deltaMode === 1 ? 16 : 1);
      if (Math.abs(distance) < 40) return;
      flipped = true;
      setDirectory(distance > 0);
    };
    node.addEventListener("wheel", wheel, { passive: false });
    return () => node.removeEventListener("wheel", wheel);
  }, []);

  const backToNavigation = () => {
    setDirectory(false);
    requestAnimationFrame(() => switchButton.current?.focus());
  };

  return (
    <aside ref={sidebar} className="sidebar flex w-56 shrink-0 flex-col border-r border-line bg-chrome p-3">
      <div className="brand brand-wordmark px-2 py-3 text-xl font-semibold">Edison</div>
      {directory && <ChannelDirectory selected={youtubeChannel} onSelect={onSelectChannel} onBack={backToNavigation} />}
      <nav className="mt-3 space-y-1" aria-label="Modules" hidden={directory}>
        <div className="flex items-center">
          <button
            data-testid="nav-youtube"
            className={`flex min-w-0 flex-1 items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${surface === "youtube" ? "bg-chromeHover text-ink" : "text-muted hover:bg-chromeHover"}`}
            onClick={onOpenYouTube}
          >
            <YouTubeIcon size={18} />
            YouTube
          </button>
          <button
            ref={switchButton}
            aria-label="打开 YouTube 频道目录"
            className="px-2 py-2 text-muted hover:text-ink"
            onClick={() => setDirectory(true)}
          >
            ›
          </button>
        </div>
        <button
          data-testid="nav-curriculum"
          className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${surface.startsWith("curriculum") ? "bg-chromeHover text-ink" : "text-muted hover:bg-chromeHover"}`}
          onClick={onOpenCurriculum}
        >
          <Icon name="table" size={18} />
          Curriculum
        </button>
      </nav>
    </aside>
  );
}

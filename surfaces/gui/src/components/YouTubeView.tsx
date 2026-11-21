import { useEffect, useRef } from "react";

export function YouTubeView({ channel }: { channel: string }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const source = "./youtube/index.html?embedded" + (import.meta.env.DEV ? "" : "&published") + "#" + encodeURIComponent(channel);
  const origin = new URL(source, location.href).origin;
  const syncTheme = () => frame.current?.contentWindow?.postMessage({
    type: "edison-theme", theme: document.documentElement.dataset.theme,
  }, origin);

  useEffect(() => {
    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, [origin]);

  return <iframe ref={frame} onLoad={syncTheme} className="block h-full w-full min-h-0 min-w-0 border-0"
    title="YouTube · 精读报告" src={source} />;
}

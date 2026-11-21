import { useEffect, useState } from "react";

type Channel = { id: string; name: string; documents: unknown[] };

export function ChannelDirectory({ selected, onSelect, onBack }: {
  selected: string;
  onSelect: (id: string) => void;
  onBack: () => void;
}) {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("./youtube/manifest.json", { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(String(response.status)); return response.json(); })
      .then(data => setChannels(data.channels as Channel[]))
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, []);
  const entries = [{ id: "", name: "全部频道", count: channels.reduce((n, c) => n + c.documents.length, 0) },
    ...channels.map(channel => ({ id: channel.id, name: channel.name, count: channel.documents.length }))];
  return <section aria-label="YouTube 频道" className="channel-directory">
    <button type="button" autoFocus onClick={onBack} aria-label="返回主导航">‹ YouTube</button>
    <div className="channel-directory-list overflow-y-auto min-h-0">
      {failed ? <p role="status">频道目录加载失败，请重新打开。</p> : entries.map(channel =>
        <button key={channel.id} aria-pressed={selected === channel.id} onClick={() => onSelect(channel.id)}>
          <span>{channel.name}</span><small>{channel.count}</small>
        </button>)}
    </div>
  </section>;
}

import { useEffect, useState } from "react";
import { YouTubeView } from "./components/YouTubeView";
import { CurriculumView } from "./components/CurriculumView";
import { CourseArchiveView } from "./components/curriculum/CourseArchiveView";
import { shanghaiToday } from "./components/curriculum/timetable";
import { Sidebar } from "./components/Sidebar";

type Surface = "youtube" | "curriculum" | "curriculum-archive";

function initialSurface(): Surface {
  const module = new URLSearchParams(location.search).get("module");
  return module === "curriculum" || module === "curriculum-archive" ? module : "youtube";
}

export function App() {
  const [surface, setSurface] = useState<Surface>(initialSurface);
  const [youtubeChannel, setYoutubeChannel] = useState("");
  const [archiveDocument, setArchiveDocument] = useState<string | null>(() =>
    new URLSearchParams(location.search).get("document"),
  );
  const [curriculumDate, setCurriculumDate] = useState(shanghaiToday);

  useEffect(() => {
    const url = new URL(location.href);
    url.searchParams.set("module", surface);
    if (surface === "curriculum-archive" && archiveDocument) {
      url.searchParams.set("document", archiveDocument);
    } else {
      url.searchParams.delete("document");
    }
    window.history.replaceState(null, "", url);
  }, [surface, archiveDocument]);

  const openArchive = (id: string | null) => {
    setArchiveDocument(id);
    setSurface("curriculum-archive");
  };

  return (
    <div className="app flex h-screen min-h-0 bg-canvas text-ink">
      <Sidebar
        surface={surface}
        youtubeChannel={youtubeChannel}
        onOpenYouTube={() => { setYoutubeChannel(""); setSurface("youtube"); }}
        onSelectChannel={(id) => { setYoutubeChannel(id); setSurface("youtube"); }}
        onOpenCurriculum={() => setSurface("curriculum")}
      />
      <main className="min-w-0 min-h-0 flex-1">
        {surface === "youtube" && <YouTubeView channel={youtubeChannel} />}
        {surface === "curriculum" && (
          <CurriculumView
            onOpenDocument={openArchive}
            onArchive={() => openArchive(null)}
            selectedDate={curriculumDate}
            setSelectedDate={setCurriculumDate}
          />
        )}
        {surface === "curriculum-archive" && (
          <CourseArchiveView
            documentId={archiveDocument}
            onOpenDocument={openArchive}
            onTimetable={() => setSurface("curriculum")}
          />
        )}
      </main>
    </div>
  );
}

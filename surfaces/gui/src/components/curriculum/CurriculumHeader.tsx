import { useTranslation } from "react-i18next";
import "./navigation.css";

export function CurriculumHeader({ view, onTimetable, onArchive }: {
  view: "timetable" | "archive";
  onTimetable: () => void;
  onArchive: () => void;
}) {
  const { t } = useTranslation();
  return <header className="curriculum-module-header">
    <h1 className="editorial-heading">Curriculum</h1>
    <nav className="curriculum-view-navigation" aria-label={t("curriculum.views")}>
      <button data-testid="curriculum-timetable" aria-current={view === "timetable" ? "page" : undefined} onClick={onTimetable}>{t("curriculum.timetable")}</button>
      <button data-testid="nav-course-archive" aria-current={view === "archive" ? "page" : undefined} onClick={onArchive}>{t("course_archive.title")}</button>
    </nav>
  </header>;
}

# Edison

Edison's product language covers the YouTube reading workbench and Curriculum.

## YouTube reading language

- **Report**: A complete, author-designed HTML document in a channel directory. Its relative path identifies it, and its original bytes are served to readers.
- **Channel**: A named folder grouping reports. Report update time orders the feed across channels.
- **Reading state**: Per-browser read and featured selections keyed by report path. Featuring a report marks it read.
- **Publication**: Edison indexes new reports after the watcher's quiet window and publishes its reading feed to the Edison GitHub Pages site.

## Curriculum language

**Curriculum（课程模块）**:
The person's university course workspace, containing the Timetable and Course archive. Personal tasks and schedule editing are outside this module's scope.
_Avoid_: Task planner, schedule editor

**Timetable（课表）**:
The weekly view of scheduled university courses, combining the academic calendar and class period times. It is distinct from the Course archive of recorded classroom documents.
_Avoid_: Course archive, schedule editor

**Course occurrence（一次课程安排）**:
A course scheduled on a particular date and time, with its assigned classroom and teacher. Separate occurrences of the same course may have different rooms or teachers.
_Avoid_: Course definition, personal task

**Course-free interval（无课时段）**:
A gap between known course commitments within a covered timetable period. It does not establish availability for other commitments.
_Avoid_: Guaranteed availability, missing timetable

**Class period（课程节次）**:
One numbered teaching interval in the university's daily timetable, with its own start and end time. A single course occurrence can contain several periods separated by breaks.
_Avoid_: Entire course occurrence, weekly course

**Classroom source transcript（课堂原始字幕）**:
The preserved, unedited transcription supplied by the classroom recording platform, including its available timestamps. It is source material for a classroom document and does not establish that every spoken passage was captured.
_Avoid_: Classroom document, corrected transcript, complete classroom record

**Classroom document（课堂整理文档）**:
A reading document organized from source material for a platform-recorded class. It can be an edited transcript or detailed revision notes; neither replaces its source transcript.
_Avoid_: Raw subtitles, course definition

**Edited classroom transcript（字幕整理稿）**:
A lightly edited, time-referenced rendering of platform captions. It may remove meaningless repetitions and fillers, correct clear typos and improve punctuation and paragraphing, while preserving substantive content, language and order without adding explanations.
_Avoid_: Summary, expanded lecture, guaranteed complete speech record

**Classroom backup（课堂本地备份）**:
A retained copy of the same reader-visible classroom document versions on the person's device. A server archive and a device backup can be current at different times.
_Avoid_: Another Edison instance, browser cache, Git push

**Recorded class（录播课次）**:
A classroom session identified and listed by the classroom recording platform. It is the unit of classroom document archiving, distinct from a scheduled course occurrence or a single numbered class period.
_Avoid_: Timetable occurrence, class period, proof of complete recording

**Supplementary classroom transcript（补充转写）**:
A transcription obtained from the recording audio to supplement absent or confirmed incomplete platform subtitles. Its source remains distinct from the preserved platform transcript.
_Avoid_: Original platform subtitles, inferred missing speech

**Course archive（课程档案）**:
The Curriculum collection of classroom documents, grouped by course by default. Source transcripts are retained separately from its reader-facing documents.
_Avoid_: Object Archive, deleted courses


## Learning Gather language

**Learning Gather（学习 Agent 空间）**:
The person's conversations with learning agents around their current core goals, including group conversations and private conversations.
_Avoid_: Human social network, general activity feed

**Core learning goal（核心学习目标）**:
A learning outcome deliberately selected by the person to guide agents' assistance. The goal is distinct from individual practice prompts and any one conversation.
_Avoid_: Reminder schedule, chat topic

**Proactive learning message（主动学习消息）**:
A message initiated by a learning agent to help the person progress toward a core learning goal. Its presence in a conversation is distinct from a notification outside Edison.
_Avoid_: External notification, proof of learning progress

**Learning notification（学习通知）**:
An optional notice outside the learning conversation that draws the person's attention to a learning message. It is independent of whether agents may create messages inside Edison.
_Avoid_: Learning message, required reply

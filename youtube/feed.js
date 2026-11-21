const list = document.querySelector("#documents");
const channels = document.querySelector("#channels");
const bulk = document.querySelector("#mark-all");
const message = document.querySelector("#message");
const publicRoot = new URL("https://vincentshuo.github.io/Edison/youtube/");
let reportRoot = new URL(".", location.href);
let reports = [];
let filter = "all";

function loadSet(name) {
  try {
    const value = JSON.parse(localStorage.getItem(name) || "[]");
    return new Set(Array.isArray(value) ? value : []);
  } catch { return new Set(); }
}
const read = loadSet("reading-report-read");
const featured = loadSet("reading-report-featured");
featured.forEach(id => read.add(id));

function save() {
  localStorage.setItem("reading-report-read", JSON.stringify([...read]));
  localStorage.setItem("reading-report-featured", JSON.stringify([...featured]));
}
function toggleRead(id) {
  if (read.has(id)) { read.delete(id); featured.delete(id); }
  else read.add(id);
  save();
  render();
}
function toggleFeatured(id) {
  if (featured.has(id)) featured.delete(id);
  else { featured.add(id); read.add(id); }
  save();
  render();
}
function stateOf(id) {
  if (featured.has(id)) return "featured";
  return read.has(id) ? "read" : "unread";
}
function element(tag, content, className) {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}
function action(label, pressed, activate) {
  const button = element("button", label);
  button.setAttribute("aria-pressed", String(pressed));
  button.onclick = activate;
  return button;
}
function row(doc) {
  const item = document.createElement("li");
  const text = document.createElement("div");
  const path = doc.path.split("/").map(encodeURIComponent).join("/");
  const title = element("a", doc.title, "title");
  title.href = new URL(path, reportRoot).href;
  title.target = "_blank";
  title.rel = "noopener";
  text.append(element("div", doc.channel + " · " + doc.date, "meta"), title);
  const actions = element("div", "", "actions");
  const share = element("a", "公开链接 ↗");
  share.href = new URL(path, publicRoot).href;
  share.target = "_blank";
  share.rel = "noopener";
  actions.append(action(read.has(doc.id) ? "已读" : "未读", read.has(doc.id), () => toggleRead(doc.id)),
    action("精选", featured.has(doc.id), () => toggleFeatured(doc.id)), share);
  item.append(text, actions);
  return item;
}
function render() {
  const group = reports.filter(doc => !channels.value || doc.channel === channels.value);
  const visible = group.filter(doc => filter === "all" || stateOf(doc.id) === filter);
  list.replaceChildren(...visible.map(row));
  document.querySelector("#count").textContent = visible.length + " 份报告";
  message.textContent = visible.length ? "" : "当前筛选下没有报告。";
  bulk.hidden = filter !== "unread" || !visible.length;
  bulk.onclick = () => { group.forEach(doc => read.add(doc.id)); save(); render(); };
  for (const button of document.querySelectorAll("[data-filter]")) {
    if (button.dataset.filter === filter) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
}
for (const button of document.querySelectorAll("[data-filter]")) {
  button.onclick = () => { filter = button.dataset.filter; render(); };
}
channels.onchange = render;
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
}
applyTheme(matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light");
window.addEventListener("message", event => {
  if (event.source === window.parent && event.data?.type === "edison-theme") applyTheme(event.data.theme);
});
async function loadManifest(root) {
  const response = await fetch(new URL("manifest.json", root));
  if (!response.ok) throw new Error(String(response.status));
  return response.json();
}
async function loadReports() {
  if (new URLSearchParams(location.search).has("published")) {
    try {
      const manifest = await loadManifest(publicRoot);
      reportRoot = publicRoot;
      return manifest;
    } catch {
      // A packaged Edison build carries a matching offline snapshot.
    }
  }
  return loadManifest(reportRoot);
}
loadReports().then(manifest => {
  for (const channel of manifest.channels) channels.add(new Option(channel.name, channel.id));
  reports = manifest.channels.flatMap(channel => channel.documents)
    .sort((a,b) => b.modified.localeCompare(a.modified) || b.path.localeCompare(a.path));
  render();
}).catch(() => { message.textContent = "报告目录加载失败，请刷新重试。"; });

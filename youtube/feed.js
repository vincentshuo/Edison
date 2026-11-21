const list = document.querySelector("#documents");
const channels = document.querySelector("#channels");
const bulk = document.querySelector("#mark-all");
const message = document.querySelector("#message");
const publicRoot = new URL("https://vincentshuo.github.io/Edison/youtube/");
let reportRoot = new URL(".", location.href);
let reports = [];
let filter = "all";
let selectedChannel = "";

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
function row(doc, index) {
  const item = document.createElement("li");
  const number = element("span", String(index + 1).padStart(2, "0"), "number");
  const path = doc.path.split("/").map(encodeURIComponent).join("/");
  const title = element("a", doc.title, "title");
  title.href = new URL(path, reportRoot).href;
  title.target = "_blank";
  title.rel = "noopener";
  title.title = doc.channel + " · " + doc.title;
  const date = element("time", doc.date, "date");
  date.dateTime = doc.modified;
  const actions = element("div", "", "actions");
  const share = element("a", "↗", "share");
  share.title = "公开链接";
  share.setAttribute("aria-label", "公开链接");
  share.href = new URL(path, publicRoot).href;
  share.target = "_blank";
  share.rel = "noopener";
  const star = action(featured.has(doc.id) ? "★" : "☆", featured.has(doc.id), () => toggleFeatured(doc.id));
  star.title = featured.has(doc.id) ? "取消精选" : "设为精选";
  star.setAttribute("aria-label", "精选");
  actions.append(action(read.has(doc.id) ? "已读" : "未读", read.has(doc.id), () => toggleRead(doc.id)),
    star, share);
  item.append(number, title, date, actions);
  return item;
}
function render() {
  const group = reports.filter(doc => !selectedChannel || doc.channel === selectedChannel);
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
const channelToggle = document.querySelector("#channel-toggle");
channelToggle.onclick = () => {
  channelToggle.setAttribute("aria-expanded", String(channelToggle.getAttribute("aria-expanded") !== "true"));
};
function addChannel(id, name, count) {
  const button = element("button", "", "channel");
  button.append(element("span", name), element("small", String(count)));
  button.setAttribute("aria-pressed", String(id === selectedChannel));
  button.onclick = () => {
    selectedChannel = id;
    channels.querySelector('[aria-pressed="true"]')?.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-pressed", "true");
    document.querySelector("#channel-name").textContent = name;
    channelToggle.setAttribute("aria-expanded", "false");
    if (channelToggle.offsetWidth) channelToggle.focus();
    document.querySelector("main").scrollTop = 0;
    render();
  };
  channels.append(button);
}
const embedded = new URLSearchParams(location.search).has("embedded") && window.parent !== window;
if (embedded) {
  document.body.classList.add("embedded");
  const selectFromSidebar = () => {
    selectedChannel = decodeURIComponent(location.hash.slice(1));
    document.querySelector("#channel-name").textContent = selectedChannel || "全部频道";
    document.querySelector("main").scrollTop = 0;
    render();
  };
  window.addEventListener("hashchange", selectFromSidebar);
  selectFromSidebar();
}
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
  reports = manifest.channels.flatMap(channel => channel.documents)
    .sort((a,b) => b.modified.localeCompare(a.modified) || b.path.localeCompare(a.path));
  addChannel("", "全部频道", reports.length);
  for (const channel of manifest.channels) addChannel(channel.id, channel.name, channel.documents.length);
  render();
}).catch(() => { message.textContent = "报告目录加载失败，请刷新重试。"; });

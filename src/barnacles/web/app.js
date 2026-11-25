// The tree: folders {type, path, name, title, description, folders, notebooks, children} and
// notebooks {type, path, title, description, mode, thumbnail?, thumbnail_dark?}.
// Routes: #/ (root), #/<folder path>/ (a folder), #/<folder path>/<slug> (a notebook).
const tree = JSON.parse(document.getElementById("notebooks").textContent);
const siteTitle = document.title;
const $ = (s) => document.querySelector(s);
const el = (tag, props = {}, ...kids) => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids.filter(Boolean));
  return e;
};
const icon = (name) => {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#i-${name}`);
  svg.append(use);
  return svg;
};
const encode = (path) => path.split("/").map(encodeURIComponent).join("/");
const href = (node) => node.type === "folder" ? (node.path ? `#/${encode(node.path)}/` : "#/") : `#/${encode(node.path)}`;
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const nameOf = (node) => node.title;

// index every node by path (folders keep a trailing "/") and remember its parents
const nodes = new Map(), parents = new Map();
(function index(folder, trail) {
  nodes.set(folder.path ? folder.path + "/" : "", folder);
  parents.set(folder, trail);
  for (const child of folder.children) {
    if (child.type === "folder") index(child, [...trail, folder]);
    else { nodes.set(child.path, child); parents.set(child, [...trail, folder]); }
  }
})(tree, []);

// ---- burger menu: Home + collapsible folder tree ----
const menu = $("#menu");
function menuItems(folder) {
  return folder.children.map((child) => {
    if (child.type === "notebook") {
      return el("a", { href: href(child), className: "nb" }, icon("notebook"), el("span", { textContent: child.title }));
    }
    const link = el("a", { href: href(child) }, icon("folder"), el("span", { textContent: child.title }),
      el("span", { className: "count", textContent: child.notebooks }));
    // clicking the name opens the folder page (and expands it) instead of toggling
    link.addEventListener("click", (e) => { e.preventDefault(); location.hash = link.getAttribute("href"); });
    const chevron = el("span", { className: "chevron" }, icon("chevron"));
    const details = el("details", {}, el("summary", {}, chevron, link),
      el("div", { className: "children" }, ...menuItems(child)));
    details.dataset.path = child.path;
    return details;
  });
}
menu.append(el("a", { href: "#/" }, icon("home"), el("span", { textContent: "Home" })), el("hr"), ...menuItems(tree));

// ---- gallery: one card per folder / notebook ----
function card(node) {
  if (node.type === "folder") {
    return el("a", { className: "card folder", href: href(node) },
      el("div", { className: "thumb" }, icon("folder")),
      el("div", { className: "body" },
        el("h3", { textContent: node.title }),
        node.description && el("p", { textContent: node.description }),
        stats(node),
        el("span", { className: "badge", textContent: "folder" })));
  }
  const thumb = node.thumbnail
    ? el("div", { className: "thumb" }, el("picture", {},
        node.thumbnail_dark && el("source", { srcset: node.thumbnail_dark, media: "(prefers-color-scheme: dark)" }),
        el("img", { src: node.thumbnail, alt: "", loading: "lazy" })))
    : el("div", { className: "thumb", textContent: node.title.charAt(0) });
  return el("a", { className: "card", href: href(node) }, thumb,
    el("div", { className: "body" },
      el("h3", { textContent: node.title }),
      node.description && el("p", { textContent: node.description }),
      el("span", { className: "badge", textContent: node.mode })));
}
function stats(folder) {
  const item = (name, n, word) => el("span", {}, icon(name), el("b", { textContent: n }), ` ${word}${n === 1 ? "" : "s"}`);
  return el("div", { className: "stats" },
    folder.folders > 0 && item("folder", folder.folders, "folder"),
    item("notebook", folder.notebooks, "notebook"));
}
function showFolder(folder) {
  $("h1").replaceChildren(folder.path ? icon("folder") : "", nameOf(folder));
  const counts = folder.notebooks
    ? [folder.folders && plural(folder.folders, "folder"), plural(folder.notebooks, "notebook")].filter(Boolean).join(" · ")
    : "No notebooks yet. Add a marimo .py file to the notebooks folder.";
  $(".lead").replaceChildren([folder.description, counts].filter(Boolean).join(" — "));
  $(".grid").replaceChildren(...folder.children.map(card));
  $("#gallery").scrollTop = 0;
}

// ---- drawer ----
const burger = $(".burger");
const setOpen = (open) => {
  document.body.classList.toggle("open", open);
  burger.setAttribute("aria-expanded", open);
};
burger.addEventListener("click", () => setOpen(!document.body.classList.contains("open")));
$(".backdrop").addEventListener("click", () => setOpen(false));
document.addEventListener("keydown", (e) => e.key === "Escape" && setOpen(false));

// ---- routing ----
const frame = $("iframe");
function route() {
  const raw = location.hash.replace(/^#\/?/, "");
  const key = raw.split("/").map(decodeURIComponent).join("/");
  const node = nodes.get(key) ?? nodes.get(key + "/") ?? tree;
  const isNotebook = node.type === "notebook";
  const src = isNotebook ? `notebooks/${encode(node.path)}/` : null;

  $("#gallery").hidden = isNotebook;
  frame.hidden = !isNotebook;
  if (isNotebook && frame.getAttribute("src") !== src) frame.src = src;
  if (!isNotebook) { frame.removeAttribute("src"); showFolder(node); } // stop a running notebook

  // breadcrumbs: every folder below the root, then the current page
  const trail = [...parents.get(node), node].filter((n) => n !== tree);
  $(".crumbs").replaceChildren(...trail.map((n, i) => el("li", {},
    i === trail.length - 1 ? el("span", { textContent: nameOf(n) }) : el("a", { href: href(n), textContent: nameOf(n) }))));
  $(".newtab").hidden = !isNotebook;
  if (isNotebook) $(".newtab").href = src;
  document.title = trail.length ? `${nameOf(node)} · ${siteTitle}` : siteTitle;

  // menu: highlight the current page and expand the folders leading to it
  const current = href(node);
  for (const a of menu.querySelectorAll("a")) {
    if (a.getAttribute("href") === current) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  const open = new Set(trail.filter((n) => n.type === "folder").map((n) => n.path));
  for (const d of menu.querySelectorAll("details")) if (open.has(d.dataset.path)) d.open = true;
  setOpen(false);
}
addEventListener("hashchange", route);
route();

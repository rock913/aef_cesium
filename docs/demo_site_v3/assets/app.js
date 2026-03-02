(async function () {
  const tabsEl = document.getElementById("tabs");
  const viewer = document.getElementById("viewer");

  async function loadConfig() {
    const res = await fetch("app.config.json", { cache: "no-store" });
    if (!res.ok) throw new Error("Cannot load app.config.json");
    return await res.json();
  }

  let config;
  try {
    config = await loadConfig();
  } catch (e) {
    console.error(e);
    return;
  }

  const pages = (config.pages || []).map((p) => ({
    id: p.id || p.title || p.file,
    title: p.title || p.id || p.file,
    file: p.file,
  }));

  if (!pages.length) return;

  let currentIdx = 0;

  function pageUrl(idx) {
    // encodeURI keeps spaces; good for "plate drift.html"
    return "pages/" + encodeURI(pages[idx].file);
  }

  function openPage(idx) {
    currentIdx = idx;
    const url = pageUrl(idx);

    [...tabsEl.children].forEach((btn, i) =>
      btn.classList.toggle("active", i === idx)
    );

    viewer.src = url;
    document.title = "4D Earth Demo - " + pages[idx].title;
  }

  // Build tabs
  tabsEl.innerHTML = "";
  pages.forEach((p, i) => {
    const btn = document.createElement("button");
    btn.className = "tab";
    btn.textContent = p.title;
    btn.onclick = () => openPage(i);
    tabsEl.appendChild(btn);
  });

  // Open default page
  const defId = config.default || pages[0].id;
  const defIdx = Math.max(
    0,
    pages.findIndex((p) => p.id === defId)
  );
  openPage(defIdx);
})();

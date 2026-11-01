// Mobile menu toggle
document.querySelectorAll("[data-nav]").forEach((nav) => {
  const button = nav.querySelector(".nav__toggle");
  if (!button) return;
  button.addEventListener("click", () => {
    const open = nav.getAttribute("data-open") === "true";
    nav.setAttribute("data-open", String(!open));
    button.setAttribute("aria-expanded", String(!open));
  });
  nav.querySelectorAll(".nav__links a").forEach((link) =>
    link.addEventListener("click", () => {
      nav.setAttribute("data-open", "false");
      button.setAttribute("aria-expanded", "false");
    })
  );
});

// Latest sermon: reads assets/data/latest-sermon.json (kept fresh by tools/update_sermon.py)
// and swaps the fallback link for an embedded player. Re-checks every 10 minutes.
document.querySelectorAll("[data-sermon]").forEach((figure) => {
  const frame = figure.querySelector(".video");
  const meta = figure.querySelector(".sermon__meta");
  let current = null;

  const render = (s) => {
    const key = s.videoId + (s.live ? ":live" : "");
    if (key === current) return;
    current = key;

    const iframe = document.createElement("iframe");
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(s.videoId)}?rel=0`;
    iframe.title = s.title || figure.dataset.label;
    iframe.allow = "accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    iframe.allowFullscreen = true;
    iframe.loading = "lazy";
    frame.replaceChildren(iframe);

    const date = new Date(`${s.date}T12:00:00`).toLocaleDateString(figure.dataset.locale, {
      weekday: "long", month: "long", day: "numeric", year: "numeric",
    });
    const label = document.createElement("span");
    label.className = s.live ? "live-badge" : "sermon__label";
    label.textContent = s.live ? figure.dataset.liveLabel : figure.dataset.label;
    const title = document.createElement("span");
    title.className = "sermon__title";
    title.textContent = s.title;
    const when = document.createElement("span");
    when.className = "sermon__date";
    when.textContent = date;
    meta.replaceChildren(label, title, when);
  };

  const load = () =>
    fetch(`${figure.dataset.src}?t=${Date.now()}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((s) => s && s.videoId && render(s))
      .catch(() => {}); // keep the fallback link

  load();
  setInterval(() => document.visibilityState === "visible" && load(), 10 * 60 * 1000);
});

// Remember the chosen language so the landing page can point to it next time
document.querySelectorAll("[data-lang-choice]").forEach((link) =>
  link.addEventListener("click", () => {
    try { localStorage.setItem("wal-lang", link.dataset.langChoice); } catch (e) {}
  })
);

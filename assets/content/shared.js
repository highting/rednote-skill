(function () {
  "use strict";
  const scene = document.body.dataset.contentScene;
  const state = {index: 0, scene, mathErrors: []};
  const pages = Array.from(document.querySelectorAll("[data-export-page]"));
  function activate(index, exporting) {
    if (!Number.isInteger(index) || index < 0 || index >= pages.length) {
      throw new RangeError("Content page index is out of range");
    }
    state.index = index;
    if (exporting) document.body.classList.add("content-exporting");
    if (scene === "report") pages.forEach((page, n) => { page.hidden = n !== index; });
    document.querySelectorAll("[data-slide-target]").forEach(button => {
      if (Number(button.dataset.slideTarget) === index) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const counter = document.querySelector("[data-page-counter]");
    if (counter) counter.textContent = (index + 1) + " / " + pages.length;
    const notes = document.querySelector("[data-notes-content]");
    const source = pages[index].querySelector("[data-speaker-notes]");
    if (notes) notes.innerHTML = source ? source.innerHTML : "<p>本页没有讲者备注。</p>";
    return pages[index];
  }
  // Renderer calls this with a zero-based index and awaits its completion.
  window.activateContentExport = async function ({index, scene: requestedScene} = {}) {
    if (requestedScene && requestedScene !== scene) throw new Error("Content scene does not match export scene");
    const target = window.contentExport.activate(index);
    target.getBoundingClientRect(); // Flush the newly activated page before waiting for its fonts.
    await window.contentExport.ready;
    await document.fonts.ready;
    return target;
  };
  window.contentExport = {state, count: () => pages.length, activate: index => activate(index, true), ready: null};
  if (scene === "report" && pages.length) {
    const reportToc = document.querySelector("[data-report-toc]");
    const reportTocToggle = document.querySelector("[data-report-toc-toggle]");
    if (reportToc && reportTocToggle) {
      const list = reportToc.querySelector("[data-report-toc-links]");
      pages.forEach((page, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.slideTarget = String(index);
        button.textContent = String(index + 1).padStart(2, "0") + " · " + (page.dataset.pageTitle || "页面 " + (index + 1));
        button.addEventListener("click", () => activate(index, false));
        list.append(button);
      });
      reportTocToggle.addEventListener("click", () => {
        reportToc.hidden = !reportToc.hidden;
        reportTocToggle.setAttribute("aria-expanded", String(!reportToc.hidden));
      });
    }
    activate(0, false);
    document.querySelector("[data-slide-prev]").addEventListener("click", () => activate(Math.max(0, state.index - 1), false));
    document.querySelector("[data-slide-next]").addEventListener("click", () => activate(Math.min(pages.length - 1, state.index + 1), false));
    document.addEventListener("keydown", event => {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName) || event.target.isContentEditable || event.target.closest("[data-keyboard-local]")) return;
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault(); activate(Math.min(pages.length - 1, state.index + 1), false);
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault(); activate(Math.max(0, state.index - 1), false);
      }
    });
  }
  const toc = document.querySelector("[data-content-toc]");
  const main = document.querySelector(".content-document");
  if (toc && main) {
    const nav = toc.querySelector("nav");
    const headings = Array.from(main.querySelectorAll("h2,h3"));
    nav.replaceChildren();
    headings.forEach((heading, index) => {
      if (!heading.id) heading.id = "content-section-" + (index + 1);
      const link = document.createElement("a");
      link.href = "#" + heading.id;
      link.className = heading.tagName === "H2" ? "toc-chapter" : "toc-section";
      const clone = heading.cloneNode(true);
      clone.querySelectorAll(".chapter-number").forEach(node => node.remove());
      if (heading.tagName === "H2" && heading.dataset.chapter) {
        const number = document.createElement("span");
        number.className = "toc-number"; number.textContent = heading.dataset.chapter;
        link.append(number);
      }
      link.append(document.createTextNode(clone.textContent.trim())); nav.append(link);
    });
    const links = Array.from(nav.querySelectorAll("a"));
    function markCurrent() {
      let current = 0;
      headings.forEach((heading, index) => {if (heading.getBoundingClientRect().top <= 130) current = index;});
      links.forEach((link, index) => {
        if (index === current) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }
    document.addEventListener("scroll", markCurrent, {passive: true}); markCurrent();
    const open = document.querySelector("[data-toc-open]");
    const close = document.querySelector("[data-toc-close]");
    function toggle(collapsed) {
      const anchor = Array.from(main.querySelectorAll("h1,h2,h3,p,figure,details")).find(node => node.getBoundingClientRect().bottom > 50);
      const top = anchor ? anchor.getBoundingClientRect().top : 0;
      toc.hidden = collapsed; open.hidden = !collapsed;
      close.setAttribute("aria-expanded", String(!collapsed)); open.setAttribute("aria-expanded", String(!collapsed));
      if (anchor) window.scrollBy({top: anchor.getBoundingClientRect().top - top, behavior: "instant"});
    }
    close.addEventListener("click", () => toggle(true)); open.addEventListener("click", () => toggle(false));
  }
  try {
    if (typeof window.renderMathInElement === "function") {
      window.renderMathInElement(document.body, {
        delimiters: [{left: "\\[", right: "\\]", display: true}, {left: "\\(", right: "\\)", display: false}],
        throwOnError: false,
        ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option", "template"],
        errorCallback: message => state.mathErrors.push(String(message))
      });
      document.querySelectorAll(".katex-error").forEach(node => state.mathErrors.push(node.textContent));
    }
  } catch (error) { state.mathErrors.push(String(error)); }
  window.contentExport.ready = document.fonts.ready.then(() => ({scene, pages: pages.length, mathErrors: state.mathErrors.slice()}));
})();

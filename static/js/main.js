document.addEventListener("DOMContentLoaded", () => {
  const scrollTop = document.querySelector(".scroll-top");
  if (scrollTop) {
    const toggleScrollTop = () => {
      scrollTop.classList.toggle("is-visible", window.scrollY > 480);
    };
    toggleScrollTop();
    window.addEventListener("scroll", toggleScrollTop, { passive: true });
    scrollTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      scrollTop.blur();
    });
  }

  const revealItems = document.querySelectorAll(".home-reveal");
  if (revealItems.length) {
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      revealItems.forEach((item) => item.classList.add("is-visible"));
    } else {
      const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        });
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
      revealItems.forEach((item, index) => {
        item.style.transitionDelay = `${Math.min(index * 45, 220)}ms`;
        revealObserver.observe(item);
      });
    }
  }

  document.querySelectorAll("[data-story-carousel]").forEach((carousel) => {
    const track = carousel.querySelector("[data-story-track]");
    const prev = carousel.querySelector("[data-story-prev]");
    const next = carousel.querySelector("[data-story-next]");
    if (!track || !prev || !next) return;
    const viewedKey = "dds_viewed_stories";
    const readViewedStories = () => {
      try {
        return new Set(JSON.parse(localStorage.getItem(viewedKey) || "[]"));
      } catch (error) {
        return new Set();
      }
    };
    const writeViewedStories = (items) => {
      localStorage.setItem(viewedKey, JSON.stringify([...items].slice(-120)));
    };
    const viewedStories = readViewedStories();
    carousel.querySelectorAll("[data-story-id]").forEach((storyLink) => {
      if (viewedStories.has(storyLink.dataset.storyId)) {
        storyLink.classList.add("is-viewed");
      }
      storyLink.addEventListener("click", () => {
        viewedStories.add(storyLink.dataset.storyId);
        writeViewedStories(viewedStories);
        storyLink.classList.add("is-viewed");
      });
    });

    const getStep = () => {
      const firstCard = track.querySelector(".story-slat");
      if (!firstCard) return Math.max(track.clientWidth * 0.75, 220);
      const styles = window.getComputedStyle(track);
      const gap = parseFloat(styles.columnGap || styles.gap || "0") || 0;
      return firstCard.getBoundingClientRect().width + gap;
    };

    const updateButtons = () => {
      const maxScroll = Math.max(track.scrollWidth - track.clientWidth - 2, 0);
      carousel.classList.toggle("is-scrollable", maxScroll > 8);
      prev.classList.toggle("is-disabled", track.scrollLeft <= 2);
      next.classList.toggle("is-disabled", track.scrollLeft >= maxScroll);
    };

    prev.addEventListener("click", () => {
      track.scrollBy({ left: -getStep() * 2, behavior: "smooth" });
    });
    next.addEventListener("click", () => {
      track.scrollBy({ left: getStep() * 2, behavior: "smooth" });
    });
    track.addEventListener("scroll", updateButtons, { passive: true });
    window.addEventListener("resize", updateButtons, { passive: true });

    let isDown = false;
    let didDrag = false;
    let suppressClick = false;
    let startX = 0;
    let startScroll = 0;

    track.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      isDown = true;
      didDrag = false;
      suppressClick = false;
      startX = event.clientX;
      startScroll = track.scrollLeft;
      track.classList.add("is-dragging");
      track.setPointerCapture(event.pointerId);
    });
    track.addEventListener("pointermove", (event) => {
      if (!isDown) return;
      const distance = event.clientX - startX;
      if (Math.abs(distance) > 6) didDrag = true;
      track.scrollLeft = startScroll - distance;
    });
    const stopDragging = (event) => {
      if (!isDown) return;
      isDown = false;
      track.classList.remove("is-dragging");
      if (track.hasPointerCapture(event.pointerId)) {
        track.releasePointerCapture(event.pointerId);
      }
      if (didDrag) {
        suppressClick = true;
      }
      window.setTimeout(() => {
        didDrag = false;
        suppressClick = false;
      }, 120);
    };
    track.addEventListener("pointerup", stopDragging);
    track.addEventListener("pointercancel", stopDragging);
    track.addEventListener("click", (event) => {
      if (!suppressClick && !didDrag) return;
      event.preventDefault();
      event.stopPropagation();
    }, true);
    updateButtons();
  });

  if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    document.querySelectorAll(".hero-main, .feature-card, .category-link, .media-card, .webstory-card, .photo-mosaic a").forEach((card) => {
      card.dataset.tilt = "true";
      card.addEventListener("mousemove", (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(900px) rotateX(${(-y * 1.6).toFixed(2)}deg) rotateY(${(x * 1.6).toFixed(2)}deg) translateY(-2px)`;
      });
      card.addEventListener("mouseleave", () => {
        card.style.transform = "";
      });
    });
  }

  const infiniteGrid = document.querySelector(".js-infinite-grid");
  const pagination = document.querySelector(".js-pagination");
  if (infiniteGrid && pagination && "IntersectionObserver" in window) {
    let loading = false;

    const loadNextPage = async () => {
      const nextLink = document.querySelector(".js-next-page");
      if (!nextLink || loading) return;
      loading = true;
      pagination.classList.add("is-loading");

      try {
        const response = await fetch(nextLink.href, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        const html = await response.text();
        const doc = new DOMParser().parseFromString(html, "text/html");
        const incomingGrid = doc.querySelector(".js-infinite-grid");
        const incomingPagination = doc.querySelector(".js-pagination");

        incomingGrid?.querySelectorAll(":scope > *").forEach((item) => {
          infiniteGrid.appendChild(document.importNode(item, true));
        });

        if (incomingPagination) {
          pagination.innerHTML = incomingPagination.innerHTML;
        } else {
          pagination.remove();
          observer.disconnect();
        }
      } catch (error) {
        pagination.classList.add("is-paused");
      } finally {
        loading = false;
        pagination.classList.remove("is-loading");
      }
    };

    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) loadNextPage();
    }, { rootMargin: "520px 0px" });

    observer.observe(pagination);
  }

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = "Copied";
    });
  });

  document.querySelectorAll("[data-share]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (navigator.share) {
        await navigator.share({ title: document.title, url: window.location.href });
      }
    });
  });

  const story = document.querySelector("[data-story]");
  if (story) {
    const slides = [...story.querySelectorAll(".story-slide")];
    const progressItems = [...story.querySelectorAll(".story-progress span")];
    const duration = Number(story.dataset.storyDuration || 5000);
    let index = 0;
    let timer = null;

    const syncProgress = () => {
      progressItems.forEach((item, itemIndex) => {
        item.classList.toggle("is-done", itemIndex < index);
        item.classList.toggle("is-active", itemIndex === index);
        if (itemIndex === index) {
          item.style.animation = "none";
          item.offsetHeight;
          item.style.animation = "";
        }
      });
    };

    const scheduleNext = () => {
      window.clearTimeout(timer);
      if (slides.length > 1) {
        timer = window.setTimeout(() => show(index + 1), duration);
      }
    };

    const show = (nextIndex) => {
      if (!slides.length) return;
      slides[index]?.classList.remove("active");
      index = (nextIndex + slides.length) % slides.length;
      slides[index]?.classList.add("active");
      syncProgress();
      scheduleNext();
    };
    story.querySelectorAll("[data-story-next]").forEach((button) => {
      button.addEventListener("click", () => show(index + 1));
    });
    story.querySelectorAll("[data-story-prev]").forEach((button) => {
      button.addEventListener("click", () => show(index - 1));
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") show(index + 1);
      if (event.key === "ArrowLeft") show(index - 1);
      if (event.key === "Escape") story.querySelector(".story-close")?.click();
    });
    let startX = 0;
    story.addEventListener("touchstart", (event) => { startX = event.touches[0].clientX; });
    story.addEventListener("touchend", (event) => {
      const diff = event.changedTouches[0].clientX - startX;
      if (Math.abs(diff) > 40) show(index + (diff < 0 ? 1 : -1));
    });
    story.addEventListener("pointerdown", () => window.clearTimeout(timer));
    story.addEventListener("pointerup", scheduleNext);
    syncProgress();
    scheduleNext();
  }
});

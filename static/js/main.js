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

    // No setPointerCapture here on purpose: capturing the pointer on `track`
    // retargets subsequent pointer events to it, and on some browsers that
    // interferes with the synthesized "click" event's own hit-testing --
    // which is exactly what made a plain (non-drag) tap on a story sometimes
    // fail to navigate. Plain track-scoped listeners are enough for this.
    track.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      isDown = true;
      didDrag = false;
      suppressClick = false;
      startX = event.clientX;
      startScroll = track.scrollLeft;
      track.classList.add("is-dragging");
    });
    track.addEventListener("pointermove", (event) => {
      if (!isDown) return;
      const distance = event.clientX - startX;
      if (Math.abs(distance) > 6) didDrag = true;
      track.scrollLeft = startScroll - distance;
    });
    const stopDragging = () => {
      if (!isDown) return;
      isDown = false;
      track.classList.remove("is-dragging");
      if (didDrag) {
        suppressClick = true;
      }
      window.setTimeout(() => {
        didDrag = false;
        suppressClick = false;
      }, 120);
    };
    // Bound on window (not just `track`) so a drag that ends with the
    // pointer outside the carousel still resets state correctly.
    window.addEventListener("pointerup", stopDragging);
    window.addEventListener("pointercancel", stopDragging);
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

  // navigator.clipboard is undefined on non-HTTPS origins and can reject when
  // permission is denied, so it needs a fallback and a visible result either way.
  const copyText = async (text) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (error) {
      /* fall through to the execCommand path below */
    }
    try {
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.setAttribute("readonly", "");
      helper.style.cssText = "position:absolute;left:-9999px;top:0";
      document.body.appendChild(helper);
      helper.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(helper);
      return ok;
    } catch (error) {
      return false;
    }
  };

  // Announce the outcome to screen readers as well as sighted users; without
  // this the button silently did nothing when the clipboard was unavailable.
  const feedback = (button, message) => {
    const original = button.dataset.originalLabel || button.textContent;
    button.dataset.originalLabel = original;
    button.textContent = message;
    button.setAttribute("aria-live", "polite");
    window.setTimeout(() => { button.textContent = original; }, 2000);
  };

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const ok = await copyText(button.dataset.copy);
      feedback(button, ok ? "कॉपी हो गया" : "कॉपी नहीं हुआ");
    });
  });

  document.querySelectorAll("[data-share]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation(); // a share button can sit inside its own card's link (e.g. Local Editions)
      // A card representing a different item (e.g. one city's edition, not
      // this page) sets data-share to that item's own URL; anything else
      // (an empty/placeholder value) falls back to sharing the current page.
      const url = button.dataset.share || window.location.href;
      // navigator.share is absent on most desktop browsers. Previously the
      // button did nothing at all there; now it falls back to copying the link.
      if (navigator.share) {
        try {
          await navigator.share({ title: document.title, url });
          return;
        } catch (error) {
          if (error && error.name === "AbortError") return; // user cancelled
        }
      }
      const ok = await copyText(url);
      feedback(button, ok ? "लिंक कॉपी हो गया" : "शेयर नहीं हो सका");
    });
  });

  const story = document.querySelector("[data-story]");
  if (story) {
    // Close should return to whichever page the reader opened this story
    // from (homepage carousel, web-stories list, an article, ...), not
    // always jump to the web-stories list. Only trust a same-origin
    // referrer that isn't another story page (avoids bouncing between two
    // stories when navigating story-to-story) and falls back to the list
    // link already in the markup when there's nothing sensible to return to.
    const closeLink = story.querySelector(".story-close");
    if (closeLink) {
      try {
        const referrer = document.referrer ? new URL(document.referrer) : null;
        if (referrer && referrer.origin === window.location.origin && referrer.href !== window.location.href) {
          closeLink.href = referrer.href;
        }
      } catch (error) {
        /* keep the default web-stories list fallback */
      }
    }

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

  // Long-form videos on the /videos/ grid play inline on the same page
  // (a normal 16:9 player), unlike Shorts which open the full-screen swipe
  // viewer -- the two are deliberately different browsing experiences.
  const videoPlayer = document.querySelector("[data-video-player]");
  if (videoPlayer) {
    const frame = videoPlayer.querySelector("[data-video-player-frame]");
    const titleEl = videoPlayer.querySelector("[data-video-player-title]");
    const closeBtn = videoPlayer.querySelector("[data-video-player-close]");
    const playBtn = videoPlayer.querySelector("[data-video-player-play]");
    const backBtn = videoPlayer.querySelector("[data-video-player-back]");
    const forwardBtn = videoPlayer.querySelector("[data-video-player-forward]");
    const restartBtn = videoPlayer.querySelector("[data-video-player-restart]");
    const muteBtn = videoPlayer.querySelector("[data-video-player-mute]");
    const volumeInput = videoPlayer.querySelector("[data-video-player-volume]");
    let ytPlayer = null;
    let apiReadyPromise = null;

    // On phones/small tablets, a video should behave like Reels/YouTube --
    // tapping it jumps straight into the full-screen autoplaying viewer
    // (video.get_absolute_url, the reels template) instead of expanding a
    // small player embedded in the page, which is the right feel on desktop
    // but awkward to reach and control with one thumb on a small screen.
    const isSmallScreen = () => window.matchMedia("(max-width: 640px)").matches;
    const loadYouTubeApi = () => {
      if (window.YT?.Player) return Promise.resolve(window.YT);
      if (apiReadyPromise) return apiReadyPromise;
      apiReadyPromise = new Promise((resolve) => {
        const previousReady = window.onYouTubeIframeAPIReady;
        window.onYouTubeIframeAPIReady = () => {
          if (typeof previousReady === "function") previousReady();
          resolve(window.YT);
        };
        if (!document.querySelector("script[src='https://www.youtube.com/iframe_api']")) {
          const script = document.createElement("script");
          script.src = "https://www.youtube.com/iframe_api";
          script.async = true;
          document.head.appendChild(script);
        }
      });
      return apiReadyPromise;
    };
    const updatePlayIcon = () => {
      if (!ytPlayer || !playBtn) return;
      const state = ytPlayer.getPlayerState?.();
      const icon = playBtn.querySelector("i");
      if (!icon) return;
      icon.className = state === 1 ? "bi bi-pause-fill" : "bi bi-play-fill";
    };
    const seekBy = (seconds) => {
      if (!ytPlayer?.getCurrentTime || !ytPlayer?.seekTo) return;
      ytPlayer.seekTo(Math.max(0, ytPlayer.getCurrentTime() + seconds), true);
    };
    const extractVideoId = (embedUrl) => {
      const match = embedUrl.match(/\/embed\/([\w-]{6,})/);
      return match ? match[1] : "";
    };
    // Same fix as the reels viewer: YT.Player's documented contract is to
    // replace a placeholder <div>, not take over an existing <iframe> -- and
    // Player#destroy() removes that element from the DOM entirely, so a
    // second "destroy + rebuild against the same reference" attempt (e.g.
    // closing and reopening a different video) would silently fail. Build
    // the player once against the div, then reuse it via loadVideoById.
    const bindPlayer = async (embed) => {
      const videoId = extractVideoId(embed);
      if (!videoId) return;
      const YT = await loadYouTubeApi();
      if (ytPlayer?.loadVideoById) {
        ytPlayer.loadVideoById(videoId);
        ytPlayer.playVideo?.();
        return;
      }
      ytPlayer = new YT.Player(frame, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: {autoplay: 1, rel: 0, origin: window.location.origin},
        events: {
          onReady: () => {
            const volume = Number(volumeInput?.value || 80);
            ytPlayer.setVolume?.(volume);
            ytPlayer.playVideo?.();
            updatePlayIcon();
          },
          onStateChange: updatePlayIcon,
        },
      });
    };

    document.querySelectorAll("[data-video-inline-card]").forEach((card) => {
      card.addEventListener("click", (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
        if (isSmallScreen()) return; // let the anchor navigate to the full-screen viewer
        const embed = card.dataset.embed;
        if (!embed) return; // no playable embed -- let it navigate to the fallback page
        event.preventDefault();
        titleEl.textContent = card.dataset.title || "";
        videoPlayer.hidden = false;
        videoPlayer.scrollIntoView({behavior: "smooth", block: "start"});
        bindPlayer(embed);
      });
    });

    closeBtn?.addEventListener("click", () => {
      ytPlayer?.pauseVideo?.();
      videoPlayer.hidden = true;
    });
    playBtn?.addEventListener("click", () => {
      if (!ytPlayer?.getPlayerState) return;
      if (ytPlayer.getPlayerState() === 1) ytPlayer.pauseVideo?.();
      else ytPlayer.playVideo?.();
      updatePlayIcon();
    });
    backBtn?.addEventListener("click", () => seekBy(-10));
    forwardBtn?.addEventListener("click", () => seekBy(10));
    restartBtn?.addEventListener("click", () => ytPlayer?.seekTo?.(0, true));
    muteBtn?.addEventListener("click", () => {
      if (!ytPlayer) return;
      const icon = muteBtn.querySelector("i");
      if (ytPlayer.isMuted?.()) {
        ytPlayer.unMute?.();
        if (icon) icon.className = "bi bi-volume-mute-fill";
      } else {
        ytPlayer.mute?.();
        if (icon) icon.className = "bi bi-volume-up-fill";
      }
    });
    volumeInput?.addEventListener("input", () => {
      const volume = Number(volumeInput.value);
      ytPlayer?.setVolume?.(volume);
      if (volume > 0) ytPlayer?.unMute?.();
    });
    document.addEventListener("keydown", (event) => {
      if (videoPlayer.hidden || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
      if (event.key === "ArrowLeft") { event.preventDefault(); seekBy(-10); }
      if (event.key === "ArrowRight") { event.preventDefault(); seekBy(10); }
      if (event.key === " ") { event.preventDefault(); playBtn?.click(); }
      if (event.key.toLowerCase() === "m") muteBtn?.click();
      if (event.key === "Escape") closeBtn?.click();
    });
  }

  // Long-form videos share the same feed_json blob as the reels viewer (it
  // carries like state/count keyed by visitor), just without the swipe UI --
  // this like button reads that blob for the one video on this page.
  const vwLikeWrap = document.querySelector("[data-vw-like-wrap]");
  if (vwLikeWrap) {
    const likeBtn = vwLikeWrap.querySelector("[data-vw-like]");
    const likeCountEl = vwLikeWrap.querySelector("[data-vw-like-count]");
    const dataEl = document.getElementById("reels-feed-data");
    const feed = dataEl ? JSON.parse(dataEl.textContent) : [];
    const index = Number(vwLikeWrap.dataset.startIndex) || 0;
    const item = feed[index];
    const csrfToken = () => {
      const meta = document.querySelector("meta[name='csrf-token']");
      if (meta && meta.content) return meta.content;
      const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : "";
    };
    if (item) {
      likeBtn.classList.toggle("is-liked", !!item.liked);
      likeBtn.querySelector("i").className = item.liked ? "bi bi-heart-fill" : "bi bi-heart";
      likeBtn?.addEventListener("click", async () => {
        const wasLiked = !!item.liked;
        item.liked = !wasLiked;
        item.likes = (item.likes || 0) + (wasLiked ? -1 : 1);
        likeBtn.classList.toggle("is-liked", item.liked);
        likeBtn.querySelector("i").className = item.liked ? "bi bi-heart-fill" : "bi bi-heart";
        likeCountEl.textContent = item.likes;
        try {
          const response = await fetch(item.like_url, {
            method: "POST",
            headers: {"X-CSRFToken": csrfToken()},
            credentials: "same-origin",
          });
          const data = await response.json();
          if (response.ok) {
            item.liked = data.liked;
            item.likes = data.likes;
          } else {
            item.liked = wasLiked;
            item.likes = (item.likes || 0) + (wasLiked ? 1 : -1);
          }
        } catch (error) {
          item.liked = wasLiked;
          item.likes = (item.likes || 0) + (wasLiked ? 1 : -1);
        }
        likeBtn.classList.toggle("is-liked", item.liked);
        likeBtn.querySelector("i").className = item.liked ? "bi bi-heart-fill" : "bi bi-heart";
        likeCountEl.textContent = item.likes;
      });
    }
  }

  // The plain long-form video watch page (not the swipe reels viewer) gets
  // its own static comment box, wired the same way as the reels one but
  // without the swipe-feed/full-screen machinery.
  const vwComments = document.querySelector("[data-vw-comments]");
  if (vwComments) {
    const listEl = vwComments.querySelector("[data-vw-comments-list]");
    const countEl = vwComments.querySelector("[data-vw-comment-count]");
    const errorEl = vwComments.querySelector("[data-vw-comment-error]");
    const form = vwComments.querySelector("[data-vw-comment-form]");
    const commentsUrl = vwComments.dataset.commentsUrl;
    const createUrl = vwComments.dataset.commentCreateUrl;
    const csrfToken = () => {
      const meta = document.querySelector("meta[name='csrf-token']");
      if (meta && meta.content) return meta.content;
      const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : "";
    };

    const escapeHtml = (value) => {
      const div = document.createElement("div");
      div.textContent = value;
      return div.innerHTML;
    };
    const renderList = (comments) => {
      countEl.textContent = comments.length;
      if (!comments.length) {
        listEl.innerHTML = '<p class="video-watch-comments-empty">अभी कोई कमेंट नहीं है — सबसे पहले आप लिखें।</p>';
        return;
      }
      listEl.innerHTML = comments.map((c) => `
        <div class="video-watch-comment-item">
          <strong>${escapeHtml(c.name)}</strong>
          <span>${escapeHtml(c.text)}</span>
          <time>${escapeHtml(c.created_at)}</time>
        </div>
      `).join("");
    };

    fetch(commentsUrl, {credentials: "same-origin"})
      .then((response) => response.json())
      .then((data) => renderList(data.comments || []))
      .catch(() => { listEl.innerHTML = '<p class="video-watch-comments-empty">कमेंट लोड नहीं हो सके।</p>'; });

    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorEl.hidden = true;
      const formData = new FormData(form);
      const name = formData.get("name").trim();
      const text = formData.get("text").trim();
      if (!name || !text) return;
      try {
        const response = await fetch(createUrl, {
          method: "POST",
          headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken()},
          credentials: "same-origin",
          body: JSON.stringify({name, text}),
        });
        const data = await response.json();
        if (!response.ok) {
          errorEl.textContent = data.error || "कमेंट भेजा नहीं जा सका।";
          errorEl.hidden = false;
          return;
        }
        const existing = listEl.querySelectorAll(".video-watch-comment-item").length;
        const current = existing && !listEl.querySelector(".video-watch-comments-empty")
          ? Array.from(listEl.querySelectorAll(".video-watch-comment-item")).map((el) => ({
              name: el.querySelector("strong").textContent,
              text: el.querySelector("span").textContent,
              created_at: el.querySelector("time").textContent,
            }))
          : [];
        renderList([data.comment, ...current]);
        form.reset();
      } catch (error) {
        errorEl.textContent = "नेटवर्क में समस्या है, दोबारा कोशिश करें।";
        errorEl.hidden = false;
      }
    });
  }

  // E-paper reader: shows each page as its own image with prev/next +
  // thumbnail navigation, like a real e-paper site -- not an embedded PDF,
  // which renders inconsistently (or not at all) across browsers/webviews.
  const epaperModal = document.querySelector("[data-epaper-modal]");
  if (epaperModal) {
    const pagesDataEl = document.getElementById("epaper-pages-data");
    const pages = pagesDataEl ? JSON.parse(pagesDataEl.textContent) : [];
    const pageImg = epaperModal.querySelector("[data-epaper-modal-page]");
    const titleEl = epaperModal.querySelector("[data-epaper-modal-title]");
    const indicatorEl = epaperModal.querySelector("[data-epaper-modal-indicator]");
    const downloadLink = epaperModal.querySelector("[data-epaper-modal-download]");
    const closeBtn = epaperModal.querySelector("[data-epaper-modal-close]");
    const prevBtn = epaperModal.querySelector("[data-epaper-modal-prev]");
    const nextBtn = epaperModal.querySelector("[data-epaper-modal-next]");
    const thumbsEl = epaperModal.querySelector("[data-epaper-modal-thumbs]");
    const wrapEl = epaperModal.querySelector("[data-epaper-modal-wrap]");
    const zoomInBtn = epaperModal.querySelector("[data-epaper-modal-zoom-in]");
    const zoomOutBtn = epaperModal.querySelector("[data-epaper-modal-zoom-out]");
    const zoomLevelEl = epaperModal.querySelector("[data-epaper-modal-zoom-level]");
    const zoomHint = epaperModal.querySelector("[data-epaper-modal-zoom-hint]");
    const pdfUrl = epaperModal.dataset.pdfUrl;
    let index = 0;

    // Zoom/pan: the image is scaled+translated via one transform, dragged
    // with pointer events while zoomed in (native overflow-scroll doesn't
    // grow to match a CSS transform, so panning has to be done manually).
    const MIN_ZOOM = 1;
    const MAX_ZOOM = 3;
    let zoom = 1;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let didDrag = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let panStartX = 0;
    let panStartY = 0;

    const applyTransform = () => {
      pageImg.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
      zoomLevelEl.textContent = `${Math.round(zoom * 100)}%`;
      wrapEl.classList.toggle("is-zoomed", zoom > 1);
      zoomOutBtn.disabled = zoom <= MIN_ZOOM;
      zoomInBtn.disabled = zoom >= MAX_ZOOM;
      if (zoomHint) zoomHint.hidden = zoom > 1;
    };
    const clampPan = () => {
      // Keeps the page from being dragged entirely off screen: the further
      // zoomed in, the more room there is to pan.
      const maxOffset = ((zoom - 1) * wrapEl.clientWidth) / 2 + 40;
      panX = Math.max(-maxOffset, Math.min(maxOffset, panX));
      const maxOffsetY = ((zoom - 1) * wrapEl.clientHeight) / 2 + 40;
      panY = Math.max(-maxOffsetY, Math.min(maxOffsetY, panY));
    };
    const setZoom = (newZoom) => {
      zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));
      if (zoom === MIN_ZOOM) { panX = 0; panY = 0; }
      clampPan();
      applyTransform();
    };
    const resetZoom = () => { zoom = 1; panX = 0; panY = 0; applyTransform(); };

    // Click toggles between fit and 2x zoom -- the quickest gesture for
    // "read this headline closer", same as tapping a photo in most apps.
    // Suppressed after an actual drag so panning doesn't also toggle zoom.
    wrapEl.addEventListener("click", () => {
      if (didDrag) { didDrag = false; return; }
      setZoom(zoom > 1 ? 1 : 2);
    });
    wrapEl.addEventListener("wheel", (event) => {
      event.preventDefault();
      setZoom(zoom - event.deltaY * 0.0015);
    }, {passive: false});

    wrapEl.addEventListener("pointerdown", (event) => {
      if (zoom <= 1) return;
      isDragging = true;
      didDrag = false;
      dragStartX = event.clientX;
      dragStartY = event.clientY;
      panStartX = panX;
      panStartY = panY;
      wrapEl.classList.add("is-dragging");
    });
    window.addEventListener("pointermove", (event) => {
      if (!isDragging) return;
      const distance = Math.hypot(event.clientX - dragStartX, event.clientY - dragStartY);
      if (distance > 4) didDrag = true;
      panX = panStartX + (event.clientX - dragStartX);
      panY = panStartY + (event.clientY - dragStartY);
      clampPan();
      applyTransform();
    });
    window.addEventListener("pointerup", () => {
      isDragging = false;
      wrapEl.classList.remove("is-dragging");
    });

    if (pages.length) {
      thumbsEl.innerHTML = pages.map((url, i) => `
        <button type="button" class="epaper-modal-thumb" data-index="${i}">
          <img src="${url}" alt="पेज ${i + 1}" loading="lazy">
          <span>${i + 1}</span>
        </button>
      `).join("");
    }

    const render = () => {
      pageImg.src = pages[index];
      indicatorEl.textContent = `पेज ${index + 1} / ${pages.length}`;
      prevBtn.disabled = index === 0;
      nextBtn.disabled = index === pages.length - 1;
      resetZoom();
      thumbsEl.querySelectorAll(".epaper-modal-thumb").forEach((thumb, i) => {
        thumb.classList.toggle("is-active", i === index);
      });
      const activeThumb = thumbsEl.querySelector(".is-active");
      activeThumb?.scrollIntoView({behavior: "smooth", inline: "center", block: "nearest"});
    };
    const goTo = (newIndex) => {
      index = Math.max(0, Math.min(pages.length - 1, newIndex));
      render();
    };

    const openModal = (title) => {
      if (!pages.length) return;
      index = 0;
      titleEl.textContent = title || "ई-पेपर";
      downloadLink.href = pdfUrl;
      render();
      epaperModal.hidden = false;
      document.body.style.overflow = "hidden";
    };
    const closeModal = () => {
      epaperModal.hidden = true;
      document.body.style.overflow = "";
    };

    document.querySelectorAll("[data-epaper-open]").forEach((trigger) => {
      trigger.addEventListener("click", () => openModal(trigger.dataset.epaperTitle));
    });
    closeBtn.addEventListener("click", closeModal);
    prevBtn.addEventListener("click", () => goTo(index - 1));
    nextBtn.addEventListener("click", () => goTo(index + 1));
    zoomInBtn.addEventListener("click", () => setZoom(zoom + 0.5));
    zoomOutBtn.addEventListener("click", () => setZoom(zoom - 0.5));
    thumbsEl.addEventListener("click", (event) => {
      const thumb = event.target.closest("[data-index]");
      if (thumb) goTo(Number(thumb.dataset.index));
    });
    document.addEventListener("keydown", (event) => {
      if (epaperModal.hidden) return;
      if (event.key === "Escape") closeModal();
      if (event.key === "ArrowLeft") goTo(index - 1);
      if (event.key === "ArrowRight") goTo(index + 1);
    });
  }

  const reels = document.querySelector("[data-reels]");
  if (reels) {
    const dataEl = document.getElementById("reels-feed-data");
    const feed = dataEl ? JSON.parse(dataEl.textContent) : [];
    const frame = reels.querySelector("[data-reels-frame]");
    const counterEl = reels.querySelector("[data-reels-counter]");
    const muteBtn = reels.querySelector("[data-reels-mute]");
    const likeBtn = reels.querySelector("[data-reels-like]");
    const likeCountEl = reels.querySelector("[data-reels-like-count]");
    const closeLink = reels.querySelector("[data-reels-close]");
    const commentOpenBtn = reels.querySelector("[data-reels-comment-open]");
    const commentCountEl = reels.querySelector("[data-reels-comment-count]");
    const commentsPanel = reels.querySelector("[data-reels-comments]");
    const commentsCloseBtn = reels.querySelector("[data-reels-comments-close]");
    const commentsList = reels.querySelector("[data-reels-comments-list]");
    const commentForm = reels.querySelector("[data-reels-comment-form]");
    const commentError = reels.querySelector("[data-reels-comment-error]");
    const reelsPlayBtn = reels.querySelector("[data-reels-play]");
    const reelsBackBtn = reels.querySelector("[data-reels-back]");
    const reelsForwardBtn = reels.querySelector("[data-reels-forward]");
    const reelsVolumeInput = reels.querySelector("[data-reels-volume]");
    let index = Math.min(Math.max(Number(reels.dataset.startIndex) || 0, 0), Math.max(feed.length - 1, 0));
    let muted = true;
    const commentCache = Object.create(null);
    let reelsPlayer = null;
    let reelsApiReadyPromise = null;
    let playerBindToken = 0;
    const playerControlEls = [reelsPlayBtn, reelsBackBtn, reelsForwardBtn, reelsVolumeInput].filter(Boolean);
    const viewedSlugs = new Set(feed[index]?.slug ? [feed[index].slug] : []);
    const setPlayerControlsEnabled = (enabled) => {
      playerControlEls.forEach((control) => { control.disabled = !enabled; });
    };
    const loadReelsYouTubeApi = () => {
      if (window.YT?.Player) return Promise.resolve(window.YT);
      if (reelsApiReadyPromise) return reelsApiReadyPromise;
      reelsApiReadyPromise = new Promise((resolve) => {
        const previousReady = window.onYouTubeIframeAPIReady;
        window.onYouTubeIframeAPIReady = () => {
          if (typeof previousReady === "function") previousReady();
          resolve(window.YT);
        };
        if (!document.querySelector("script[src='https://www.youtube.com/iframe_api']")) {
          const script = document.createElement("script");
          script.src = "https://www.youtube.com/iframe_api";
          script.async = true;
          document.head.appendChild(script);
        }
      });
      return reelsApiReadyPromise;
    };
    const updateReelsPlayIcon = () => {
      const icon = reelsPlayBtn?.querySelector("i");
      if (!icon || !reelsPlayer?.getPlayerState) return;
      icon.className = reelsPlayer.getPlayerState() === 1 ? "bi bi-pause-fill" : "bi bi-play-fill";
    };
    // Extracts the raw YouTube video id out of the nocookie embed URL
    // (".../embed/<id>?...") so a page switch can call loadVideoById on the
    // existing player instead of tearing it down and rebuilding it.
    const extractVideoId = (embedUrl) => {
      const match = embedUrl.match(/\/embed\/([\w-]{6,})/);
      return match ? match[1] : "";
    };

    // IMPORTANT: YT.Player#destroy() removes the <iframe> element from the
    // DOM entirely. Calling it on every swipe and then re-constructing a new
    // YT.Player against that now-detached `frame` reference is why only the
    // first video ever actually played -- every following swipe built a
    // player against an element no longer in the page. The fix: build the
    // player once, then reuse it via loadVideoById() for every other video.
    const loadReelsVideo = async (item) => {
      const videoId = extractVideoId(item.embed_url);
      if (!videoId) return;
      const bindToken = ++playerBindToken;
      setPlayerControlsEnabled(false);
      const YT = await loadReelsYouTubeApi();
      if (bindToken !== playerBindToken) return;

      if (reelsPlayer?.loadVideoById) {
        reelsPlayer.loadVideoById(videoId);
        if (muted) reelsPlayer.mute?.();
        else reelsPlayer.unMute?.();
        reelsPlayer.setVolume?.(Number(reelsVolumeInput?.value || 80));
        reelsPlayer.playVideo?.();
        setPlayerControlsEnabled(true);
        updateReelsPlayIcon();
        return;
      }

      reelsPlayer = new YT.Player(frame, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: {
          autoplay: 1,
          mute: muted ? 1 : 0,
          playsinline: 1,
          rel: 0,
          // Reels/Shorts should feel like a native app, not an embedded
          // YouTube widget: no scrubber/controls, no end-screen suggestions,
          // no captions/annotations/keyboard/fullscreen chrome.
          controls: 0,
          disablekb: 1,
          fs: 0,
          iv_load_policy: 3,
          modestbranding: 1,
          cc_load_policy: 0,
          origin: window.location.origin,
        },
        events: {
          onReady: () => {
            if (bindToken !== playerBindToken) return;
            const volume = Number(reelsVolumeInput?.value || 80);
            reelsPlayer.setVolume?.(volume);
            if (muted) reelsPlayer.mute?.();
            else reelsPlayer.unMute?.();
            reelsPlayer.playVideo?.();
            setPlayerControlsEnabled(true);
            updateReelsPlayIcon();
          },
          onStateChange: (event) => {
            if (bindToken !== playerBindToken) return;
            updateReelsPlayIcon();
            // Loop the current video in place -- swiping is the only way to
            // move to a different one, so "ended" should never dead-end on
            // a paused frame or YouTube's related-videos end screen.
            if (event.data === window.YT.PlayerState.ENDED) {
              reelsPlayer.seekTo(0, true);
              reelsPlayer.playVideo();
            }
          },
        },
      });
    };
    const seekReelsBy = (seconds) => {
      if (!reelsPlayer?.getCurrentTime || !reelsPlayer?.seekTo) return;
      reelsPlayer.seekTo(Math.max(0, reelsPlayer.getCurrentTime() + seconds), true);
    };
    const csrfToken = () => {
      const meta = document.querySelector("meta[name='csrf-token']");
      if (meta && meta.content) return meta.content;
      const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : "";
    };
    const recordView = async (item) => {
      if (!item?.view_url || viewedSlugs.has(item.slug)) return;
      viewedSlugs.add(item.slug);
      try {
        const response = await fetch(item.view_url, {
          method: "POST",
          headers: {"X-CSRFToken": csrfToken()},
          credentials: "same-origin",
        });
        if (!response.ok) return;
        const data = await response.json();
        if (typeof data.views === "number") {
          item.views = data.views;
        }
      } catch (error) {
        /* keep the optimistic local UI if the analytics ping fails */
      }
    };

    // Same "return to wherever you came from" behaviour as the web-story
    // viewer, so closing a reel doesn't dump you on the generic video list
    // when you opened it from the homepage, an article, etc.
    if (closeLink) {
      try {
        const referrer = document.referrer ? new URL(document.referrer) : null;
        if (referrer && referrer.origin === window.location.origin && referrer.href !== window.location.href) {
          closeLink.href = referrer.href;
        }
      } catch (error) {
        /* keep the default videos-list fallback */
      }
    }

    if (!feed.length) {
      reels.innerHTML = '<div class="reels-empty">कोई वीडियो उपलब्ध नहीं है।</div>';
    } else {
      function renderComments(list) {
        if (!list.length) {
          commentsList.innerHTML = '<p class="reels-comments-empty">अभी कोई कमेंट नहीं है — सबसे पहले आप लिखें।</p>';
          return;
        }
        commentsList.innerHTML = list.map((c) => `
          <div class="reels-comment-item">
            <strong>${escapeHtml(c.name)}</strong>
            <span>${escapeHtml(c.text)}</span>
            <time>${escapeHtml(c.created_at)}</time>
          </div>
        `).join("");
      }

      function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value;
        return div.innerHTML;
      }
      function syncActionState(item) {
        commentCountEl.textContent = item.comment_count || 0;
        likeCountEl.textContent = item.likes || 0;
        likeBtn.classList.toggle("is-liked", !!item.liked);
        likeBtn.querySelector("i").className = item.liked ? "bi bi-heart-fill" : "bi bi-heart";
      }

      async function loadComments(item) {
        if (commentCache[item.slug]) {
          renderComments(commentCache[item.slug]);
          return;
        }
        commentsList.innerHTML = '<p class="reels-comments-empty">लोड हो रहा है...</p>';
        try {
          const response = await fetch(item.comments_url, {credentials: "same-origin"});
          const data = await response.json();
          commentCache[item.slug] = data.comments || [];
          renderComments(commentCache[item.slug]);
        } catch (error) {
          commentsList.innerHTML = '<p class="reels-comments-empty">कमेंट लोड नहीं हो सके।</p>';
        }
      }

      const render = () => {
        const item = feed[index];
        counterEl.textContent = `${index + 1} / ${feed.length}`;
        muteBtn.querySelector("i").className = muted ? "bi bi-volume-mute-fill" : "bi bi-volume-up-fill";
        muteBtn.classList.toggle("is-unmuted", !muted);
        syncActionState(item);
        commentsPanel.classList.remove("is-open");
        window.history.replaceState(null, "", item.url);
        document.title = `${item.title} - Desh Darpan Samvad`;
        loadReelsVideo(item);
        recordView(item);
      };

      const go = (nextIndex) => {
        index = (nextIndex + feed.length) % feed.length;
        render();
      };

      muteBtn.addEventListener("click", () => {
        muted = !muted;
        if (muted) reelsPlayer?.mute?.();
        else reelsPlayer?.unMute?.();
        muteBtn.classList.toggle("is-unmuted", !muted);
        muteBtn.querySelector("i").className = muted ? "bi bi-volume-mute-fill" : "bi bi-volume-up-fill";
      });
      reelsPlayBtn?.addEventListener("click", () => {
        if (!reelsPlayer?.getPlayerState) return;
        if (reelsPlayer.getPlayerState() === 1) reelsPlayer.pauseVideo?.();
        else reelsPlayer.playVideo?.();
        updateReelsPlayIcon();
      });
      reelsBackBtn?.addEventListener("click", () => seekReelsBy(-10));
      reelsForwardBtn?.addEventListener("click", () => seekReelsBy(10));
      reelsVolumeInput?.addEventListener("input", () => {
        const volume = Number(reelsVolumeInput.value);
        reelsPlayer?.setVolume?.(volume);
        if (volume > 0) {
          muted = false;
          reelsPlayer?.unMute?.();
          muteBtn.classList.add("is-unmuted");
          muteBtn.querySelector("i").className = "bi bi-volume-up-fill";
        }
      });
      likeBtn.addEventListener("click", async () => {
        const item = feed[index];
        // Optimistic toggle so the heart pops instantly; corrected from the
        // server response if the request fails or a rate limit kicks in.
        const wasLiked = !!item.liked;
        item.liked = !wasLiked;
        item.likes = (item.likes || 0) + (wasLiked ? -1 : 1);
        syncActionState(item);
        try {
          const response = await fetch(item.like_url, {
            method: "POST",
            headers: {"X-CSRFToken": csrfToken()},
            credentials: "same-origin",
          });
          const data = await response.json();
          if (!response.ok) {
            item.liked = wasLiked;
            item.likes = (item.likes || 0) + (wasLiked ? 1 : -1);
          } else {
            item.liked = data.liked;
            item.likes = data.likes;
          }
        } catch (error) {
          item.liked = wasLiked;
          item.likes = (item.likes || 0) + (wasLiked ? 1 : -1);
        }
        if (feed[index] === item) syncActionState(item);
      });
      reels.querySelectorAll("[data-reels-next]").forEach((button) => {
        button.addEventListener("click", () => go(index + 1));
      });
      reels.querySelectorAll("[data-reels-prev]").forEach((button) => {
        button.addEventListener("click", () => go(index - 1));
      });
      document.addEventListener("keydown", (event) => {
        if (commentsPanel.classList.contains("is-open")) {
          if (event.key === "Escape") commentsPanel.classList.remove("is-open");
          return;
        }
        if (event.key === "ArrowLeft") { event.preventDefault(); seekReelsBy(-10); }
        if (event.key === "ArrowRight") { event.preventDefault(); seekReelsBy(10); }
        if (event.key === " ") { event.preventDefault(); reelsPlayBtn?.click(); }
        if (event.key.toLowerCase() === "m") muteBtn?.click();
        if (event.key === "ArrowDown") go(index + 1);
        if (event.key === "ArrowUp") go(index - 1);
        if (event.key === "Escape") closeLink?.click();
      });
      let startY = 0;
      reels.addEventListener("touchstart", (event) => { startY = event.touches[0].clientY; });
      reels.addEventListener("touchend", (event) => {
        if (commentsPanel.classList.contains("is-open")) return;
        const diff = event.changedTouches[0].clientY - startY;
        if (Math.abs(diff) > 40) go(index + (diff < 0 ? 1 : -1));
      });

      // Desktop equivalent of the touch swipe -- one wheel "tick" changes one
      // video. Locked for a short window after firing so a single trackpad
      // scroll gesture (which fires many small wheel events) doesn't skip
      // several videos at once.
      let wheelLocked = false;
      reels.addEventListener("wheel", (event) => {
        if (commentsPanel.classList.contains("is-open")) return;
        event.preventDefault();
        if (wheelLocked || Math.abs(event.deltaY) < 12) return;
        wheelLocked = true;
        go(index + (event.deltaY > 0 ? 1 : -1));
        window.setTimeout(() => { wheelLocked = false; }, 500);
      }, {passive: false});

      commentOpenBtn.addEventListener("click", () => {
        commentsPanel.classList.add("is-open");
        loadComments(feed[index]);
      });
      commentsCloseBtn.addEventListener("click", () => commentsPanel.classList.remove("is-open"));
      commentsPanel.addEventListener("click", (event) => {
        if (event.target === commentsPanel) commentsPanel.classList.remove("is-open");
      });

      commentForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        commentError.hidden = true;
        const item = feed[index];
        const formData = new FormData(commentForm);
        const name = formData.get("name").trim();
        const text = formData.get("text").trim();
        if (!name || !text) return;
        try {
          const response = await fetch(item.comment_create_url, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken()},
            credentials: "same-origin",
            body: JSON.stringify({name, text}),
          });
          const data = await response.json();
          if (!response.ok) {
            commentError.textContent = data.error || "कमेंट भेजा नहीं जा सका।";
            commentError.hidden = false;
            return;
          }
          commentCache[item.slug] = [data.comment, ...(commentCache[item.slug] || [])];
          renderComments(commentCache[item.slug]);
          item.comment_count = data.comment_count;
          commentCountEl.textContent = data.comment_count;
          commentForm.reset();
        } catch (error) {
          commentError.textContent = "नेटवर्क में समस्या है, दोबारा कोशिश करें।";
          commentError.hidden = false;
        }
      });

      render();
    }
  }
});

(() => {
  "use strict";

  const inputQueue = [];
  const keyCounts = new Map();
  const pointerKeys = new Map();
  const controlSelector = "[data-game-key]";
  const touchQuery = window.matchMedia("(pointer: coarse)");

  const isTouchDevice = () =>
    navigator.maxTouchPoints > 0 || touchQuery.matches;

  const isPortrait = () => window.innerHeight > window.innerWidth;

  const enqueue = (type, key) => {
    inputQueue.push({ type, key });
  };

  const setPressedStyle = (key, pressed) => {
    document
      .querySelectorAll(`${controlSelector}[data-game-key="${key}"]`)
      .forEach((button) => {
        button.classList.toggle("is-pressed", pressed);
      });
  };

  const pressKey = (key) => {
    const count = keyCounts.get(key) || 0;
    keyCounts.set(key, count + 1);
    if (count === 0) {
      setPressedStyle(key, true);
      enqueue("down", key);
    }
  };

  const releaseKey = (key) => {
    const count = keyCounts.get(key) || 0;
    if (count <= 1) {
      keyCounts.delete(key);
      setPressedStyle(key, false);
      if (count > 0) {
        enqueue("up", key);
      }
      return;
    }
    keyCounts.set(key, count - 1);
  };

  const keyAtPoint = (x, y) => {
    const target = document.elementFromPoint(x, y);
    const control = target ? target.closest(controlSelector) : null;
    return control ? control.dataset.gameKey : null;
  };

  const movePointer = (pointerId, key) => {
    const previous = pointerKeys.get(pointerId) || null;
    if (previous === key) {
      return;
    }
    if (previous) {
      releaseKey(previous);
      pointerKeys.delete(pointerId);
    }
    if (key) {
      pressKey(key);
      pointerKeys.set(pointerId, key);
    }
  };

  const releasePointer = (pointerId) => {
    movePointer(pointerId, null);
  };

  const releaseAll = () => {
    for (const key of keyCounts.keys()) {
      setPressedStyle(key, false);
      enqueue("up", key);
    }
    keyCounts.clear();
    pointerKeys.clear();
  };

  const updateLayoutState = () => {
    const touch = isTouchDevice();
    document.body.classList.toggle("game-touch-enabled", touch);
    document.body.classList.toggle("game-portrait", touch && isPortrait());
  };

  document.addEventListener("pointerdown", (event) => {
    const control = event.target.closest(controlSelector);
    if (!control) {
      return;
    }
    event.preventDefault();
    try {
      control.setPointerCapture?.(event.pointerId);
    } catch (error) {
      if (error.name !== "NotFoundError") {
        throw error;
      }
    }
    movePointer(event.pointerId, control.dataset.gameKey);
  });

  document.addEventListener("pointermove", (event) => {
    if (!pointerKeys.has(event.pointerId)) {
      return;
    }
    event.preventDefault();
    movePointer(event.pointerId, keyAtPoint(event.clientX, event.clientY));
  });

  document.addEventListener("pointerup", (event) => {
    if (!pointerKeys.has(event.pointerId)) {
      return;
    }
    event.preventDefault();
    releasePointer(event.pointerId);
  });

  document.addEventListener("pointercancel", (event) => {
    releasePointer(event.pointerId);
  });

  document.addEventListener("contextmenu", (event) => {
    if (event.target.closest(controlSelector)) {
      event.preventDefault();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (
      [
        "ArrowLeft",
        "ArrowRight",
        "ArrowUp",
        "ArrowDown",
        "KeyE",
        "KeyF",
        "Escape",
      ].includes(event.code)
    ) {
      event.preventDefault();
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (
      event.target.closest(controlSelector) ||
      event.target.closest("#game-rotate-overlay")
    ) {
      return;
    }
    if (event.target.tagName === "CANVAS") {
      enqueue("down", "Enter");
      enqueue("up", "Enter");
    }
  });

  window.addEventListener("blur", releaseAll);
  window.addEventListener("resize", () => {
    releaseAll();
    updateLayoutState();
  });
  window.addEventListener("orientationchange", () => {
    releaseAll();
    updateLayoutState();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      releaseAll();
    }
  });
  touchQuery.addEventListener?.("change", updateLayoutState);

  window.gameConsumeInput = () => JSON.stringify(inputQueue.splice(0));
  window.gameReleaseControls = releaseAll;
  window.gameIsSuspended = () =>
    document.hidden || (isTouchDevice() && isPortrait());

  updateLayoutState();
})();

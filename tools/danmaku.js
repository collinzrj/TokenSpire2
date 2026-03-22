// Paste this into the browser console on the Xiaohongshu live dashboard (直播中控台)
// It polls for new comments and sends them to the TokenSpire2 viewer server

(function() {
  const SERVER = "http://localhost:5555";
  const POLL_INTERVAL = 2000;
  let seenComments = new Set();
  let initialized = false;

  function getComments() {
    // Find all comment elements in the 实时互动 section
    const items = document.querySelectorAll('.comment-item, [class*="comment"], [class*="chat-item"], [class*="message-item"]');
    const comments = [];
    items.forEach(el => {
      const text = el.textContent.trim();
      if (text && text.length > 0 && text.length < 200) {
        comments.push(text);
      }
    });
    // Fallback: try to get text content from the interaction area
    if (comments.length === 0) {
      const area = document.querySelector('[class*="interaction"], [class*="实时互动"]');
      if (area) {
        area.querySelectorAll('div, p, span').forEach(el => {
          const t = el.textContent.trim();
          // Filter: must have colon (name: message) pattern or be a chat message
          if (t && t.includes(':') && t.length > 2 && t.length < 200 && el.children.length === 0) {
            comments.push(t);
          }
        });
      }
    }
    return comments;
  }

  function poll() {
    const allComments = getComments();

    if (!initialized) {
      // First run: mark all existing comments as seen
      allComments.forEach(c => seenComments.add(c));
      initialized = true;
      console.log(`[Danmaku] Initialized, ${seenComments.size} existing comments skipped`);
      return;
    }

    const newComments = allComments.filter(c => !seenComments.has(c));
    newComments.forEach(c => seenComments.add(c));

    if (newComments.length > 0) {
      console.log(`[Danmaku] ${newComments.length} new:`, newComments);
      fetch(SERVER + "/api/comment", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({comments: newComments})
      }).catch(e => console.error("[Danmaku] Send error:", e));
    }
  }

  setInterval(poll, POLL_INTERVAL);
  poll();
  console.log("[Danmaku] TokenSpire2 comment bridge started. Polling every " + POLL_INTERVAL + "ms");
})();

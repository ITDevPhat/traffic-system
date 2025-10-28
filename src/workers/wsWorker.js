/*
  Lightweight worker to offload JSON.parse from the main thread.
  Receives raw WebSocket message text and posts parsed object back.
*/
self.onmessage = (e) => {
  try {
    const data = JSON.parse(e.data);
    self.postMessage(data);
  } catch (err) {
    // Silently ignore malformed messages to keep stream smooth
  }
};



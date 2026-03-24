import axios from "axios";

const api = axios.create({ baseURL: process.env.REACT_APP_API_URL });

export const askText = (text, history) =>
  api.post("/api/v1/ask", { text, history });

export const voiceAsk = (formData) =>
  api.post("/api/v1/voice-ask", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const transcribeAudio = (formData) =>
  api.post("/api/v1/transcribe", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const speak = (text) =>
  api.post("/api/v1/speak", { text }, { responseType: "arraybuffer" });

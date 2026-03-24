import React, { useState, useRef, useEffect } from "react";
import {
  Box, TextField, Button, CircularProgress, Alert, Typography,
  Paper, IconButton, Tooltip, Chip, Divider, List, ListItem,
  ListItemText, Avatar, LinearProgress,
} from "@mui/material";
import MicIcon from "@mui/icons-material/Mic";
import StopIcon from "@mui/icons-material/Stop";
import SendIcon from "@mui/icons-material/Send";
import VolumeUpIcon from "@mui/icons-material/VolumeUp";
import DeleteIcon from "@mui/icons-material/Delete";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import PersonIcon from "@mui/icons-material/Person";
import { askText, speak, voiceAsk } from "../services/voiceApi";

const SAMPLE_QUESTIONS = [
  "What is Python?",
  "What is FastAPI?",
  "What is LangGraph?",
  "How does Whisper work?",
  "What is FAISS?",
];

export default function VoicePage() {
  const [text, setText] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const [playingIdx, setPlayingIdx] = useState(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  // ── Text ask ──────────────────────────────────────────────────────────
  const handleAsk = async (question = text) => {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setText("");
    try {
      const r = await askText(question, history);
      setHistory(r.data.history);
    } catch (e) {
      setError(e.response?.data?.detail || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  // ── Voice recording ───────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        await handleVoiceAsk(blob);
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      setError("Microphone access denied.");
    }
  };

  const stopRecording = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };

  const handleVoiceAsk = async (blob) => {
    setLoading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", blob, "recording.webm");
      fd.append("history", JSON.stringify(history));
      const r = await voiceAsk(fd);
      const data = r.data;
      setHistory(data.history);
      // Auto-play TTS response if audio returned
      if (data.audio_base64) {
        playBase64Audio(data.audio_base64);
      }
    } catch (e) {
      setError(e.response?.data?.detail || "Voice processing failed.");
    } finally {
      setLoading(false);
    }
  };

  // ── TTS playback ──────────────────────────────────────────────────────
  const playBase64Audio = (b64) => {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
  };

  const handleSpeak = async (answer, idx) => {
    setPlayingIdx(idx);
    try {
      const r = await speak(answer);
      const blob = new Blob([r.data], { type: "audio/wav" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => setPlayingIdx(null);
      audio.play();
    } catch {
      setPlayingIdx(null);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "80vh" }}>

      {/* ── Chat history ── */}
      <Paper variant="outlined" sx={{ flex: 1, overflow: "auto", p: 2, mb: 2 }}>
        {history.length === 0 && (
          <Box sx={{ textAlign: "center", mt: 6, color: "text.secondary" }}>
            <SmartToyIcon sx={{ fontSize: 48, mb: 1, opacity: 0.3 }} />
            <Typography>Ask me anything — by voice or text</Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, justifyContent: "center", mt: 2 }}>
              {SAMPLE_QUESTIONS.map((q) => (
                <Chip key={q} label={q} size="small" variant="outlined"
                  onClick={() => handleAsk(q)} clickable />
              ))}
            </Box>
          </Box>
        )}

        <List disablePadding>
          {history.map((turn, i) => (
            <Box key={i}>
              {/* User bubble */}
              <ListItem alignItems="flex-start" sx={{ justifyContent: "flex-end", px: 0 }}>
                <Paper sx={{ p: 1.5, maxWidth: "75%", bgcolor: "primary.main", color: "white", borderRadius: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                    <PersonIcon fontSize="small" />
                    <Typography variant="caption">You</Typography>
                  </Box>
                  <Typography variant="body2">{turn.user}</Typography>
                </Paper>
              </ListItem>

              {/* Assistant bubble */}
              <ListItem alignItems="flex-start" sx={{ px: 0 }}>
                <Paper sx={{ p: 1.5, maxWidth: "75%", bgcolor: "grey.100", borderRadius: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                    <SmartToyIcon fontSize="small" color="primary" />
                    <Typography variant="caption" color="primary">Assistant</Typography>
                    <Tooltip title="Play response">
                      <IconButton size="small" onClick={() => handleSpeak(turn.assistant, i)}
                        disabled={playingIdx === i}>
                        {playingIdx === i
                          ? <CircularProgress size={14} />
                          : <VolumeUpIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                  </Box>
                  <Typography variant="body2">{turn.assistant}</Typography>
                </Paper>
              </ListItem>
              {i < history.length - 1 && <Divider sx={{ my: 0.5 }} />}
            </Box>
          ))}
        </List>
        <div ref={chatEndRef} />
      </Paper>

      {loading && <LinearProgress sx={{ mb: 1 }} />}
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}

      {/* ── Input row ── */}
      <Box sx={{ display: "flex", gap: 1, alignItems: "flex-end" }}>
        {/* Voice record button */}
        <Tooltip title={recording ? "Stop recording" : "Record voice"}>
          <IconButton
            onClick={recording ? stopRecording : startRecording}
            color={recording ? "error" : "primary"}
            sx={{
              width: 48, height: 48,
              bgcolor: recording ? "error.light" : "primary.light",
              animation: recording ? "pulse 1s infinite" : "none",
              "@keyframes pulse": {
                "0%": { boxShadow: "0 0 0 0 rgba(244,67,54,0.4)" },
                "70%": { boxShadow: "0 0 0 10px rgba(244,67,54,0)" },
                "100%": { boxShadow: "0 0 0 0 rgba(244,67,54,0)" },
              },
            }}
          >
            {recording ? <StopIcon /> : <MicIcon />}
          </IconButton>
        </Tooltip>

        <TextField
          fullWidth multiline maxRows={3}
          placeholder="Type your question or press the mic to speak…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); }
          }}
          size="small"
        />

        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Send">
            <span>
              <IconButton color="primary" onClick={() => handleAsk()}
                disabled={!text.trim() || loading}>
                {loading ? <CircularProgress size={20} /> : <SendIcon />}
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Clear chat">
            <IconButton onClick={() => setHistory([])} disabled={!history.length}>
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {recording && (
        <Typography variant="caption" color="error" sx={{ mt: 0.5, textAlign: "center" }}>
          🔴 Recording… press Stop when done
        </Typography>
      )}
    </Box>
  );
}

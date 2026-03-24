import React from "react";
import { AppBar, Toolbar, Typography, Chip, Box } from "@mui/material";
import MicIcon from "@mui/icons-material/Mic";

export default function Header() {
  return (
    <AppBar position="static" sx={{ bgcolor: "#1a1a2e" }}>
      <Toolbar sx={{ gap: 1 }}>
        <MicIcon sx={{ color: "#e94560" }} />
        <Typography variant="h6" fontWeight="bold">
          Voice AI Assistant
        </Typography>
        <Box sx={{ ml: 2, display: "flex", gap: 1 }}>
          {["Whisper STT", "LangGraph", "Ollama LLM", "Coqui TTS"].map((t) => (
            <Chip key={t} label={t} size="small"
              sx={{ bgcolor: "rgba(233,69,96,0.2)", color: "white", borderColor: "#e94560" }}
              variant="outlined"
            />
          ))}
        </Box>
      </Toolbar>
    </AppBar>
  );
}

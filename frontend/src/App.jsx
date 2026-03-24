import React from "react";
import { Container } from "@mui/material";
import Header from "./components/Header";
import VoicePage from "./pages/VoicePage";

export default function App() {
  return (
    <>
      <Header />
      <Container maxWidth="md" sx={{ py: 4 }}>
        <VoicePage />
      </Container>
    </>
  );
}

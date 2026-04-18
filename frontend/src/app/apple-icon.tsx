import { ImageResponse } from "next/og";

// Icône pour l'Écran d'accueil iOS (180x180).
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 130,
          fontWeight: 900,
          background: "linear-gradient(135deg, #0ea5e9, #0369a1)",
          color: "white",
        }}
      >
        S
      </div>
    ),
    { ...size },
  );
}

import { ImageResponse } from "next/og";

// OpenGraph image générée à la volée pour /
// Affichée en preview sur LinkedIn, Twitter, Slack, etc.

export const alt = "Secretary — Secrétariat automatique Microsoft 365, édité par Meoxa";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, #020617 0%, #0c4a6e 50%, #0369a1 100%)",
          color: "white",
          padding: "80px",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            fontSize: "32px",
            fontWeight: 600,
            color: "#7dd3fc",
            marginBottom: "24px",
          }}
        >
          Secretary. · by Meoxa
        </div>
        <div
          style={{
            fontSize: "72px",
            fontWeight: 800,
            lineHeight: 1.1,
            marginBottom: "32px",
          }}
        >
          Le secrétariat automatique
          <br />
          dans Microsoft 365
        </div>
        <div
          style={{
            fontSize: "28px",
            color: "#cbd5e1",
            lineHeight: 1.4,
            maxWidth: "900px",
          }}
        >
          Emails, réunions Teams, agenda : Secretary automatise
          <br />
          ce qui te fait perdre 2 heures par jour.
        </div>
        <div
          style={{
            marginTop: "48px",
            fontSize: "36px",
            fontWeight: 700,
            color: "#38bdf8",
          }}
        >
          1 490 € HT / an
        </div>
      </div>
    ),
    { ...size },
  );
}

import { ImageResponse } from "next/og";

// OG image générée à la volée — preview LinkedIn, Twitter, Slack, etc.
// Satori (sous ImageResponse) exige `display: flex` sur tout parent
// avec plusieurs enfants. On évite donc les <br /> en découpant en blocs.

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
            display: "flex",
          }}
        >
          Secretary. · by Meoxa
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            fontSize: "72px",
            fontWeight: 800,
            lineHeight: 1.1,
            marginBottom: "32px",
          }}
        >
          <div style={{ display: "flex" }}>Le secrétariat automatique</div>
          <div style={{ display: "flex" }}>dans Microsoft 365</div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            fontSize: "28px",
            color: "#cbd5e1",
            lineHeight: 1.4,
            maxWidth: "900px",
          }}
        >
          <div style={{ display: "flex" }}>Emails, réunions Teams, agenda : Secretary automatise</div>
          <div style={{ display: "flex" }}>ce qui te fait perdre 2 heures par jour.</div>
        </div>

        <div
          style={{
            marginTop: "48px",
            fontSize: "36px",
            fontWeight: 700,
            color: "#38bdf8",
            display: "flex",
          }}
        >
          1 490 € HT / an
        </div>
      </div>
    ),
    { ...size },
  );
}

import { ImageResponse } from "next/og";

// Favicon généré — un "S" sur fond brand.
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 22,
          fontWeight: 900,
          background: "linear-gradient(135deg, #0ea5e9, #0369a1)",
          color: "white",
          borderRadius: 6,
        }}
      >
        S
      </div>
    ),
    { ...size },
  );
}

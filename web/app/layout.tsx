import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Auto Shorts Translator",
  description: "YouTube to Korean dubbed video",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

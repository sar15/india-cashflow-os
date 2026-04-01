import type { ReactNode } from "react";

import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "India Cashflow OS",
  description: "A 13-week cash forecast cockpit for Indian SMEs and CA-led finance workflows."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

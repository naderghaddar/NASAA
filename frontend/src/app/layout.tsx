import type { Metadata } from "next";
import "./globals.css";
import ReactQueryProvider from "./react-query-provider";

export const metadata: Metadata = {
  title: "Farm Dashboard",
  description: "Irrigation & Advisory",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </body>
    </html>
  );
}

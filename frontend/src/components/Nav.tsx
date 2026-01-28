"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  const onLogout = () => {
    clearToken();
    router.push("/login");
  };

  const item = (href: string, label: string) => (
    <Link
      href={href}
      style={{
        padding: "8px 10px",
        borderRadius: 6,
        textDecoration: "none",
        color: pathname === href ? "#111" : "#444",
        background: pathname === href ? "#eaeaea" : "transparent",
      }}
    >
      {label}
    </Link>
  );

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        alignItems: "center",
        padding: 12,
        borderBottom: "1px solid #eee",
      }}
    >
      <div style={{ fontWeight: 600, marginRight: 16 }}>AI Scientist WebAPP</div>
      {item("/runs", "Runs")}
      {item("/runs/new", "New Run")}
      {item("/prompts", "Prompts")}
      <div style={{ flex: 1 }} />
      <button
        onClick={onLogout}
        style={{
          border: "1px solid #ddd",
          background: "#fff",
          padding: "6px 10px",
          borderRadius: 6,
          cursor: "pointer",
        }}
      >
        退出
      </button>
    </div>
  );
}


"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await login(email, password);
      setToken(res.access_token);
      router.push("/runs");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420 }}>
      <h2>登录</h2>
      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="邮箱"
          style={{ padding: 10, border: "1px solid #ddd", borderRadius: 6 }}
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          placeholder="密码"
          style={{ padding: 10, border: "1px solid #ddd", borderRadius: 6 }}
        />
        <button
          disabled={loading}
          style={{ padding: 10, borderRadius: 6, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}
        >
          {loading ? "登录中..." : "登录"}
        </button>
        {error ? <div style={{ color: "#b00020" }}>{error}</div> : null}
      </form>
      <div style={{ marginTop: 12 }}>
        还没有账号？<Link href="/register">去注册</Link>
      </div>
    </div>
  );
}


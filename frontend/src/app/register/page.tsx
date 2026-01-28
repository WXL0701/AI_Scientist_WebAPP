"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { register } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function RegisterPage() {
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
      const res = await register(email, password);
      setToken(res.access_token);
      router.push("/runs");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420 }}>
      <h2>注册</h2>
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
          {loading ? "注册中..." : "注册"}
        </button>
        {error ? <div style={{ color: "#b00020" }}>{error}</div> : null}
      </form>
      <div style={{ marginTop: 12 }}>
        已有账号？<Link href="/login">去登录</Link>
      </div>
    </div>
  );
}


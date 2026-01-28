"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listRuns, RunRow } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function RunsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    const load = async () => {
      try {
        setError(null);
        const data = await listRuns();
        setRuns(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载失败");
      }
    };
    load();
    const t = window.setInterval(load, 3000);
    return () => window.clearInterval(t);
  }, [router]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Runs</h2>
        <Link href="/runs/new">创建 Run</Link>
      </div>
      {error ? <div style={{ color: "#b00020" }}>{error}</div> : null}
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              {["RunID", "创建时间", "最后修改", "状态", "ProjectID", "YAML", "操作"].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>
                  <Link href={`/runs/${r.id}`}>{r.id}</Link>
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{r.created_at}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{r.updated_at}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{r.status}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{r.project_id}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{r.yaml_filename}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>
                  <Link href={`/runs/${r.id}`}>详情</Link>
                </td>
              </tr>
            ))}
            {runs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: 8, color: "#666" }}>
                  暂无 Runs
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}


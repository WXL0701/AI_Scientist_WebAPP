"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Artifact,
  cancelRun,
  DbTaskRow,
  downloadBlob,
  getArtifacts,
  getRun,
  getStages,
  RunRow,
} from "@/lib/api";
import { getToken } from "@/lib/auth";

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function RunDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [run, setRun] = useState<RunRow | null>(null);
  const [tasks, setTasks] = useState<DbTaskRow[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedMd, setSelectedMd] = useState<string | null>(null);
  const [mdText, setMdText] = useState<string>("");

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    const load = async () => {
      try {
        setError(null);
        const r = await getRun(runId);
        setRun(r);
        const s = await getStages(runId);
        setTasks(s.tasks);
        const a = await getArtifacts(runId);
        setArtifacts(a);
      } catch (err) {
        setError(err instanceof Error ? err.message : "加载失败");
      }
    };
    load();
    const t = window.setInterval(load, 2000);
    return () => window.clearInterval(t);
  }, [router, runId]);

  useEffect(() => {
    const loadMd = async () => {
      if (!selectedMd) return;
      try {
        const blob = await downloadBlob(runId, selectedMd);
        const text = await blob.text();
        setMdText(text);
      } catch (err) {
        setMdText(err instanceof Error ? err.message : "加载失败");
      }
    };
    loadMd();
  }, [runId, selectedMd]);

  const onCancel = async () => {
    try {
      await cancelRun(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取消失败");
    }
  };

  const taskTable = useMemo(() => {
    return (
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              {["task_id", "stage", "status", "updated_at", "content", "result_path"].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #eee" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{t.id}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{t.stage}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{t.status}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{t.updated_at}</td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2", maxWidth: 420 }}>
                  <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t.content}</div>
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #f2f2f2" }}>{t.result_path}</td>
              </tr>
            ))}
            {tasks.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: 8, color: "#666" }}>
                  暂无阶段信息（可能还未生成 sqlite）
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    );
  }, [tasks]);

  const mdList = artifacts.filter((a) => a.kind === "md");
  const dbList = artifacts.filter((a) => a.kind === "db");
  const logList = artifacts.filter((a) => a.kind === "log");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ margin: 0 }}>Run 详情</h2>
        <div style={{ color: "#666" }}>{runId}</div>
        <div style={{ flex: 1 }} />
        {run?.status === "running" ? (
          <button
            onClick={onCancel}
            style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}
          >
            取消
          </button>
        ) : null}
      </div>

      {error ? <div style={{ color: "#b00020" }}>{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>基本信息</div>
          <div>状态：{run?.status || "-"}</div>
          <div>创建：{run?.created_at || "-"}</div>
          <div>更新：{run?.updated_at || "-"}</div>
          <div>ProjectID：{run?.project_id || "-"}</div>
          <div>YAML：{run?.yaml_filename || "-"}</div>
          <div>Container：{run?.container_id || "-"}</div>
          <div>ExitCode：{run?.exit_code ?? "-"}</div>
        </div>
        <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>下载</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {dbList.map((a) => (
              <button
                key={a.path}
                onClick={async () => saveBlob(await downloadBlob(runId, a.path), a.path.split("/").pop() || "db.sqlite3")}
                style={{ textAlign: "left", border: "1px solid #ddd", background: "#fff", padding: 8, borderRadius: 6, cursor: "pointer" }}
              >
                DB: {a.path}
              </button>
            ))}
            {logList.map((a) => (
              <button
                key={a.path}
                onClick={async () => saveBlob(await downloadBlob(runId, a.path), a.path.split("/").pop() || "stdout.log")}
                style={{ textAlign: "left", border: "1px solid #ddd", background: "#fff", padding: 8, borderRadius: 6, cursor: "pointer" }}
              >
                Log: {a.path}
              </button>
            ))}
            {dbList.length === 0 && logList.length === 0 ? <div style={{ color: "#666" }}>暂无可下载文件</div> : null}
          </div>
        </div>
      </div>

      <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>阶段状态</div>
        {taskTable}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 12 }}>
        <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>MD 列表</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {mdList.map((a) => (
              <button
                key={a.path}
                onClick={() => setSelectedMd(a.path)}
                style={{
                  textAlign: "left",
                  border: "1px solid #ddd",
                  background: selectedMd === a.path ? "#f2f2f2" : "#fff",
                  padding: 8,
                  borderRadius: 6,
                  cursor: "pointer",
                }}
              >
                {a.stage || "stage"} / {a.task_id || ""} / {a.path.split("/").pop()}
              </button>
            ))}
            {mdList.length === 0 ? <div style={{ color: "#666" }}>暂无 md</div> : null}
          </div>
        </div>
        <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>MD 预览</div>
          <pre style={{ whiteSpace: "pre-wrap", overflowX: "auto", fontFamily: "monospace" }}>{mdText || "选择左侧 md"}</pre>
        </div>
      </div>
    </div>
  );
}


"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  baselinePromptfiles,
  createPromptSet,
  createPromptVersion,
  listPromptSets,
  listPromptVersions,
  PromptSet,
  PromptVersionMeta,
} from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function PromptsPage() {
  const router = useRouter();
  const [sets, setSets] = useState<PromptSet[]>([]);
  const [selectedSetId, setSelectedSetId] = useState<number | null>(null);
  const [versions, setVersions] = useState<PromptVersionMeta[]>([]);
  const [newSetName, setNewSetName] = useState("");
  const [notes, setNotes] = useState("");
  const [payloadText, setPayloadText] = useState("{}");
  const [baseline, setBaseline] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    baselinePromptfiles()
      .then((b) => {
        setBaseline(b.baseline);
      })
      .catch(() => {});

    listPromptSets()
      .then((s) => {
        setSets(s);
      })
      .catch(() => {});
  }, [router]);

  useEffect(() => {
    if (!selectedSetId) {
      setVersions([]);
      return;
    }
    listPromptVersions(selectedSetId)
      .then((v) => {
        setVersions(v);
      })
      .catch(() => {});
  }, [selectedSetId]);

  const onCreateSet = async () => {
    setError(null);
    try {
      const s = await createPromptSet(newSetName);
      setNewSetName("");
      setSelectedSetId(s.id);
      const nextSets = await listPromptSets();
      setSets(nextSets);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  };

  const onCreateVersion = async () => {
    if (!selectedSetId) return;
    setError(null);
    try {
      const payload = JSON.parse(payloadText) as Record<string, string>;
      await createPromptVersion(selectedSetId, notes, payload);
      setNotes("");
      const v = await listPromptVersions(selectedSetId);
      setVersions(v);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  };

  const baselineKeys = useMemo(() => Object.keys(baseline).sort(), [baseline]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 1100 }}>
      <h2 style={{ margin: 0 }}>Prompts</h2>
      {error ? <div style={{ color: "#b00020" }}>{error}</div> : null}
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 12 }}>
        <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>PromptSets</div>
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <input
              value={newSetName}
              onChange={(e) => setNewSetName(e.target.value)}
              placeholder="新 PromptSet 名称"
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, flex: 1 }}
            />
            <button
              onClick={onCreateSet}
              style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}
            >
              创建
            </button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {sets.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedSetId(s.id)}
                style={{
                  textAlign: "left",
                  border: "1px solid #ddd",
                  background: selectedSetId === s.id ? "#f2f2f2" : "#fff",
                  padding: 8,
                  borderRadius: 6,
                  cursor: "pointer",
                }}
              >
                {s.name}
              </button>
            ))}
            {sets.length === 0 ? <div style={{ color: "#666" }}>暂无 PromptSet</div> : null}
          </div>
        </div>
        <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>新建版本</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
            <div>当前 PromptSet：{selectedSetId ?? "-"}</div>
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="备注"
              style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, minWidth: 260 }}
            />
            <button
              disabled={!selectedSetId}
              onClick={onCreateVersion}
              style={{ padding: "8px 12px", borderRadius: 6, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}
            >
              保存新版本
            </button>
          </div>
          <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div style={{ marginBottom: 6, color: "#444" }}>payload（JSON：filename → system_message 内容）</div>
              <textarea
                value={payloadText}
                onChange={(e) => setPayloadText(e.target.value)}
                rows={16}
                style={{ width: "100%", padding: 10, border: "1px solid #ddd", borderRadius: 6, fontFamily: "monospace" }}
              />
            </div>
            <div>
              <div style={{ marginBottom: 6, color: "#444" }}>baseline keys</div>
              <div style={{ border: "1px solid #ddd", borderRadius: 6, padding: 10, height: 360, overflowY: "auto" }}>
                {baselineKeys.map((k) => (
                  <div key={k} style={{ padding: "4px 0", borderBottom: "1px solid #f2f2f2" }}>
                    {k}
                  </div>
                ))}
                {baselineKeys.length === 0 ? <div style={{ color: "#666" }}>未加载 baseline</div> : null}
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>版本列表</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {versions.map((v) => (
                <div key={v.id} style={{ padding: 8, border: "1px solid #eee", borderRadius: 6 }}>
                  v{v.version} (id={v.id}) {v.notes ? `- ${v.notes}` : ""}
                </div>
              ))}
              {selectedSetId && versions.length === 0 ? <div style={{ color: "#666" }}>暂无版本</div> : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createRun, listPromptSets, listPromptVersions, PromptSet, PromptVersionMeta } from "@/lib/api";
import { getToken } from "@/lib/auth";

type PromptVersionOption = { id: number; label: string };

const defaultYaml = `project_name: demo_project
username: ignored
max_workers: 1
content: |
  请在这里写入你的研究目标/假设/证明等内容。`;

export default function NewRunPage() {
  const router = useRouter();
  const [yamlText, setYamlText] = useState(defaultYaml);
  const [yamlFilename, setYamlFilename] = useState("challenge.yaml");
  const [projectId, setProjectId] = useState("");
  const [promptVersionId, setPromptVersionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState<PromptVersionOption[]>([]);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    const load = async () => {
      const sets: PromptSet[] = await listPromptSets();
      const opts: PromptVersionOption[] = [];
      for (const s of sets) {
        const versions: PromptVersionMeta[] = await listPromptVersions(s.id);
        for (const v of versions) {
          opts.push({ id: v.id, label: `${s.name} v${v.version} (id=${v.id})` });
        }
      }
      setOptions(opts);
    };
    load().catch(() => {});
  }, [router]);

  const promptSelect = useMemo(() => {
    return (
      <select
        value={promptVersionId ?? ""}
        onChange={(e) => setPromptVersionId(e.target.value ? Number(e.target.value) : null)}
        style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6 }}
      >
        <option value="">使用默认 prompts（不覆盖）</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    );
  }, [options, promptVersionId]);

  const onSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const run = await createRun(yamlText, yamlFilename, projectId, promptVersionId);
      router.push(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 1000 }}>
      <h2 style={{ margin: 0 }}>创建 Run</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div>YAML 文件名</div>
          <input
            value={yamlFilename}
            onChange={(e) => setYamlFilename(e.target.value)}
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, minWidth: 240 }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div>Project ID（可选）</div>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            style={{ padding: 8, border: "1px solid #ddd", borderRadius: 6, minWidth: 240 }}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div>Prompt Version</div>
          {promptSelect}
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div>YAML 内容</div>
        <textarea
          value={yamlText}
          onChange={(e) => setYamlText(e.target.value)}
          rows={18}
          style={{ padding: 10, border: "1px solid #ddd", borderRadius: 6, fontFamily: "monospace" }}
        />
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button
          onClick={onSubmit}
          disabled={loading}
          style={{ padding: "10px 14px", borderRadius: 6, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}
        >
          {loading ? "启动中..." : "启动 Run"}
        </button>
        {error ? <div style={{ color: "#b00020" }}>{error}</div> : null}
      </div>
    </div>
  );
}


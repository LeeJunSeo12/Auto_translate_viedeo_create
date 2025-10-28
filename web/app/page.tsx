"use client";
import { useCallback, useState } from "react";
import { z } from "zod";

const CreateJobSchema = z.object({
  youtubeUrl: z.string().url(),
  options: z.any().optional(),
});

type CreateJobResponse = { jobId: string };

export default function HomePage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<any>(undefined);
  const [dropActive, setDropActive] = useState(false);

  const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDropActive(false);
    setError(null);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      setOptions(json);
    } catch (err: any) {
      setError("JSON 파싱 실패");
    }
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const parsed = CreateJobSchema.safeParse({ youtubeUrl: url, options });
    if (!parsed.success) {
      setError("유효한 YouTube URL을 입력해주세요.");
      return;
    }
    try {
      setLoading(true);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtubeUrl: url, options }),
      });
      if (!res.ok) throw new Error("작업 생성 실패");
      const data = (await res.json()) as CreateJobResponse;
      window.location.href = `/job/${data.jobId}`;
    } catch (err: any) {
      setError(err.message || "오류가 발생했습니다");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1>Auto Shorts Translator</h1>
      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={onSubmit}>
          <input className="input" placeholder="YouTube URL" value={url} onChange={(e) => setUrl(e.target.value)} />
          <div
            onDragOver={(e) => { e.preventDefault(); setDropActive(true); }}
            onDragLeave={() => setDropActive(false)}
            onDrop={handleDrop}
            style={{ marginTop: 12, padding: 16, borderRadius: 8, border: `1px dashed ${dropActive ? "#60a5fa" : "#374151"}` }}
          >
            <div style={{ opacity: 0.9 }}>옵션 JSON 드래그&드롭 (선택)</div>
            {options && (
              <pre className="log" style={{ marginTop: 8, maxHeight: 160, overflow: "auto" }}>{JSON.stringify(options, null, 2)}</pre>
            )}
          </div>
          <div style={{ marginTop: 12 }}>
            <button className="button" disabled={loading}>{loading ? "시작 중..." : "Start"}</button>
          </div>
        </form>
        {error && <p style={{ color: "#fca5a5", marginTop: 8 }}>{error}</p>}
      </div>
    </div>
  );
}

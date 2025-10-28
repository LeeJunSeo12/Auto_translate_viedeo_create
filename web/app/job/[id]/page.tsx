"use client";
import { useEffect, useMemo, useRef, useState } from "react";

type JobStatus = "QUEUED" | "RUNNING" | "FAILED" | "DONE";

type JobStatusResponse = {
  status: JobStatus;
  progress: number;
  resultUrl?: string;
  logs?: string[];
  error?: string;
};

export default function JobPage({ params }: { params: { id: string } }) {
  const jobId = params.id;
  const [state, setState] = useState<JobStatusResponse>({ status: "QUEUED", progress: 0 });
  const [logText, setLogText] = useState("");
  const esRef = useRef<EventSource | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  const resultUrl = useMemo(() => (state.resultUrl ? `${apiBase}${state.resultUrl}` : undefined), [state.resultUrl, apiBase]);

  useEffect(() => {
    fetch(`${apiBase}/jobs/${jobId}`).then((r) => r.json()).then((d: JobStatusResponse) => setState(d)).catch(() => {});
    const es = new EventSource(`${apiBase}/stream/${jobId}`);
    esRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "status") {
          setState((prev) => ({ ...prev, ...data }));
        } else if (data.type === "result") {
          setState((prev) => ({ ...prev, resultUrl: data.result_url || data.resultUrl }));
        } else if (data.type === "log") {
          setLogText((t) => `${t}${t ? "\n" : ""}${data.message}`);
        }
      } catch {}
    };
    es.onerror = () => {
      // SSE 연결이 종료되면 폴백으로 주기적 조회
      es.close();
      const iv = setInterval(async () => {
        const r = await fetch(`${apiBase}/jobs/${jobId}`);
        if (r.ok) {
          const d = (await r.json()) as JobStatusResponse;
          setState(d);
          if (d.logs) setLogText(d.logs.join("\n"));
          if (d.status === "DONE" || d.status === "FAILED") clearInterval(iv);
        }
      }, 1500);
      return () => clearInterval(iv);
    };
    return () => es.close();
  }, [apiBase, jobId]);

  return (
    <div className="container">
      <h2>Job: {jobId}</h2>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="progress"><div style={{ width: `${state.progress}%` }} /></div>
        <p style={{ marginTop: 8 }}>상태: {state.status} ({state.progress}%)</p>
        {state.error && <p style={{ color: "#fca5a5" }}>{state.error}</p>}
        {resultUrl && (
          <div style={{ marginTop: 12 }}>
            <a className="button" href={resultUrl} download>Download Result</a>
            <div style={{ marginTop: 12 }}>
              <video controls src={resultUrl} style={{ width: "100%", borderRadius: 12 }} />
            </div>
          </div>
        )}
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <div className="log">{logText || (state.logs || []).join("\n")}</div>
      </div>
    </div>
  );
}

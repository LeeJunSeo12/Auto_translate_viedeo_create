"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

type JobStatus = "QUEUED" | "RUNNING" | "FAILED" | "DONE";

type JobStatusResponse = {
  status: JobStatus;
  progress: number;
  resultUrl?: string;
  logs?: string[];
  error?: string;
};

export default function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [state, setState] = useState<JobStatusResponse>({ status: "QUEUED", progress: 0 });
  const [logText, setLogText] = useState("");
  const esRef = useRef<EventSource | null>(null);
  const [sseStatus, setSseStatus] = useState<"connecting" | "open" | "error">("connecting");
  const [sseError, setSseError] = useState<string | null>(null);
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);

  // params를 async로 처리
  useEffect(() => {
    params.then((p) => setJobId(p.id));
  }, [params]);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const resultUrl = useMemo(() => (state.resultUrl ? `${apiBase}${state.resultUrl}` : undefined), [state.resultUrl, apiBase]);

  useEffect(() => {
    if (!jobId) return;
    fetch(`${apiBase}/jobs/${jobId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`GET /jobs/${jobId} failed: ${r.status}`);
        return r.json();
      })
      .then((d: JobStatusResponse) => setState(d))
      .catch((e) => setSseError(String(e?.message || e)));
    const es = new EventSource(`${apiBase}/stream/${jobId}`);
    esRef.current = es;
    es.onopen = () => {
      setSseStatus("open");
      setSseError(null);
    };
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        setLastEventAt(Date.now());
        if (data.type === "status") {
          setState((prev) => ({ ...prev, ...data }));
        } else if (data.type === "result") {
          setState((prev) => ({ ...prev, resultUrl: data.result_url || data.resultUrl }));
        } else if (data.type === "log") {
          setLogText((t) => `${t}${t ? "\n" : ""}${data.message}`);
        }
      } catch {}
    };
    es.onerror = (err) => {
      setSseStatus("error");
      setSseError("SSE connection error; falling back to polling");
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

  if (!jobId) return <div>Loading...</div>;

  return (
    <div className="container">
      <h2>Job: {jobId}</h2>
      <Link href="/">Home</Link>
      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ fontSize: 14, opacity: 0.9 }}>
          <div>SSE 상태: {sseStatus}</div>
          {lastEventAt && <div>마지막 이벤트: {new Date(lastEventAt).toLocaleString()}</div>}
          {sseError && <div style={{ color: "#fca5a5" }}>오류: {sseError}</div>}
          <div>API Base: {apiBase}</div>
        </div>
      </div>
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

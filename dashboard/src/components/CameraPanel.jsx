import { useEffect, useMemo, useState } from "react";
import { Camera, Circle, Power, RefreshCw, VideoOff } from "lucide-react";
import { cameraStreamUrl, getJson, postJson } from "../lib/api";

export default function CameraPanel({ status }) {
  const [vision, setVision] = useState({
    enabled: false,
    frame_available: false,
    camera_topic: "/camera/image_raw",
    stream_url: "/api/vision/camera/stream"
  });
  const [loading, setLoading] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  const active = Boolean(vision.enabled);
  const frameAvailable = Boolean(vision.frame_available);
  const streamSrc = useMemo(
    () => `${cameraStreamUrl()}?session=${streamKey}`,
    [streamKey]
  );

  async function loadVisionStatus() {
    const data = await getJson("/api/vision/status");
    setVision(data);
  }

  async function toggleVision() {
    setLoading(true);
    try {
      const endpoint = active ? "/api/vision/stop" : "/api/vision/start";
      const data = await postJson(endpoint);
      setVision(data);
      setStreamKey(Date.now());
    } finally {
      setLoading(false);
    }
  }

  function refreshStream() {
    setStreamKey(Date.now());
    loadVisionStatus();
  }

  useEffect(() => {
    loadVisionStatus();
    const interval = window.setInterval(loadVisionStatus, 2500);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-4 border-b border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 p-5 text-white md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-slate-300">
            <Camera className="h-4 w-4" />
            Vision Module
          </div>
          <h2 className="mt-2 text-2xl font-bold">Jupiter Camera View</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-300">
            Live webcam output from the robot is embedded here, so operators can monitor JUNO without a separate ROS camera pop-up.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-2 text-sm text-slate-100 ring-1 ring-white/15">
            <Circle className={`h-2.5 w-2.5 ${active ? "fill-emerald-400 text-emerald-400" : "fill-slate-500 text-slate-500"}`} />
            {active ? "Vision on" : "Vision off"}
          </span>
          <button
            onClick={refreshStream}
            className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-2 text-sm font-medium text-white ring-1 ring-white/15 hover:bg-white/15"
            type="button"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={toggleVision}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm disabled:opacity-60"
            type="button"
          >
            <Power className="h-4 w-4" />
            {loading ? "Updating..." : active ? "Switch Off" : "Switch On"}
          </button>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[1.7fr_1fr]">
        <div className="relative aspect-video bg-slate-950">
          {active && (
            <img
              key={streamKey}
              src={streamSrc}
              alt="Live camera feed from the Jupiter robot"
              className="h-full w-full object-contain"
            />
          )}

          {(!active || !frameAvailable) && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/90 p-6 text-center text-white">
              <div className="rounded-full bg-white/10 p-4 ring-1 ring-white/15">
                <VideoOff className="h-8 w-8 text-slate-200" />
              </div>
              <p className="mt-4 text-lg font-semibold">
                {active ? "Waiting for camera frames" : "Vision module is switched off"}
              </p>
              <p className="mt-2 max-w-md text-sm text-slate-300">
                {active
                  ? "The dashboard is ready. Start the ROS camera node or check the webcam device if the feed does not appear."
                  : "Switch on the vision module to show the Jupiter webcam output in this dashboard window."}
              </p>
            </div>
          )}
        </div>

        <div className="flex flex-col justify-between gap-5 bg-slate-50 p-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">Camera status</p>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex items-center justify-between rounded-2xl bg-white px-4 py-3 ring-1 ring-slate-200">
                <dt className="text-slate-500">ROS topic</dt>
                <dd className="font-medium text-slate-900">{vision.camera_topic}</dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white px-4 py-3 ring-1 ring-slate-200">
                <dt className="text-slate-500">Frames</dt>
                <dd className="font-medium text-slate-900">{frameAvailable ? "Receiving" : "Not detected"}</dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white px-4 py-3 ring-1 ring-slate-200">
                <dt className="text-slate-500">Emotion estimate</dt>
                <dd className="font-medium capitalize text-slate-900">{status?.current_emotion ?? "unknown"}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            <p className="font-medium text-slate-900">Operator note</p>
            <p className="mt-1">
              The camera feed is for interaction monitoring and visible emotion estimation. It is not a medical diagnosis or identity verification tool.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

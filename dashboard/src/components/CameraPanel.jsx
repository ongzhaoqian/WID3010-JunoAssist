import { useEffect, useMemo, useState } from "react";
import {
  Camera,
  Circle,
  Eye,
  Power,
  RefreshCw,
  Sparkles,
  Video,
  VideoOff
} from "lucide-react";
import { cameraStreamUrl, getJson, postJson } from "../lib/api";

export default function CameraPanel({ status }) {
  const [vision, setVision] = useState({
    camera_enabled: false,
    vision_model_enabled: false,
    frame_available: false,
    camera_topic: "/camera/image_raw",
    stream_url: "/api/vision/camera/stream",
    model_loaded: false
  });
  const [loadingAction, setLoadingAction] = useState(null);
  const [streamKey, setStreamKey] = useState(Date.now());

  const cameraOn = Boolean(vision.camera_enabled);
  const visionModelOn = Boolean(vision.vision_model_enabled);
  const frameAvailable = Boolean(vision.frame_available);
  const emotionLabel = visionModelOn ? (vision.emotion ?? status?.current_emotion ?? "unknown") : "Not running";
  const emotionConfidence = Number(vision.emotion_confidence ?? status?.emotion_confidence ?? 0);
  const emotionSource = vision.emotion_source ?? status?.emotion_source ?? "none";
  const analysisDescription = vision.analysis_description ?? "";
  const analysisError = vision.analysis_error ?? null;
  const streamSrc = useMemo(
    () => `${cameraStreamUrl()}?session=${streamKey}`,
    [streamKey]
  );

  async function loadVisionStatus() {
    const data = await getJson("/api/vision/status");
    setVision(data);
  }

  async function toggleCamera() {
    setLoadingAction("camera");
    try {
      const endpoint = cameraOn
        ? "/api/vision/camera/stop"
        : "/api/vision/camera/start";
      const data = await postJson(endpoint);
      setVision(data);
      setStreamKey(Date.now());
    } finally {
      setLoadingAction(null);
    }
  }

  async function toggleVisionModel() {
    if (!cameraOn) return;
    setLoadingAction("model");
    try {
      const endpoint = visionModelOn
        ? "/api/vision/model/stop"
        : "/api/vision/model/start";
      const data = await postJson(endpoint);
      setVision(data);
    } finally {
      setLoadingAction(null);
    }
  }

  async function refreshStream() {
    setLoadingAction("refresh");
    try {
      const data = await postJson("/api/vision/camera/refresh");
      setVision(data);
      setStreamKey(Date.now());
    } finally {
      setLoadingAction(null);
    }
  }

  useEffect(() => {
    loadVisionStatus();
    const interval = window.setInterval(loadVisionStatus, 2500);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <section className="glass-card overflow-hidden rounded-[2rem] text-slate-100">
      <div className="flex flex-col gap-5 border-b border-white/10 bg-gradient-to-br from-slate-950/85 via-indigo-950/70 to-fuchsia-950/55 p-5 text-white lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-slate-300">
            <Camera className="h-4 w-4" />
            Camera & Vision Control
          </div>
          <h2 className="mt-2 text-2xl font-bold">Jupiter Camera View</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-300">
            Choose when to show the live robot webcam. The Vision Module is separate, so the camera can be used as a simple monitor without running emotion recognition.
          </p>
        </div>

        <div className="grid gap-2 sm:grid-cols-3 lg:min-w-[520px]">
          <button
            onClick={toggleCamera}
            disabled={loadingAction === "camera"}
            className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold shadow-sm transition ${
              cameraOn
                ? "bg-emerald-400 text-slate-950 hover:bg-emerald-300"
                : "bg-white text-slate-950 hover:bg-slate-100"
            } disabled:opacity-60`}
            type="button"
          >
            <Power className="h-4 w-4" />
            {loadingAction === "camera" ? "Updating..." : cameraOn ? "Camera On" : "Switch On Camera"}
          </button>

          <button
            onClick={toggleVisionModel}
            disabled={!cameraOn || loadingAction === "model"}
            className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold shadow-sm transition ${
              visionModelOn
                ? "bg-violet-400 text-slate-950 hover:bg-violet-300"
                : "bg-white/10 text-white ring-1 ring-white/15 hover:bg-white/15"
            } disabled:cursor-not-allowed disabled:opacity-45`}
            type="button"
            title={cameraOn ? "Toggle emotion recognition" : "Switch on the camera first"}
          >
            <Sparkles className="h-4 w-4" />
            {loadingAction === "model" ? "Updating..." : visionModelOn ? "Vision On" : "Vision Module"}
          </button>

          <button
            onClick={refreshStream}
            disabled={loadingAction === "refresh"}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white/10 px-4 py-3 text-sm font-semibold text-white ring-1 ring-white/15 transition hover:bg-white/15 disabled:opacity-60"
            type="button"
          >
            <RefreshCw className={`h-4 w-4 ${loadingAction === "refresh" ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-0 lg:grid-cols-[1.75fr_1fr]">
        <div className="relative aspect-video bg-slate-950">
          {cameraOn && (
            <img
              key={streamKey}
              src={streamSrc}
              alt="Live camera feed from the Jupiter robot"
              className="h-full w-full object-contain"
            />
          )}

          {(!cameraOn || !frameAvailable) && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/92 p-6 text-center text-white">
              <div className="rounded-full bg-white/10 p-4 ring-1 ring-white/15">
                {cameraOn ? (
                  <Video className="h-8 w-8 text-slate-200" />
                ) : (
                  <VideoOff className="h-8 w-8 text-slate-200" />
                )}
              </div>
              <p className="mt-4 text-lg font-semibold">
                {cameraOn ? "Waiting for Jupiter camera frames" : "Camera is switched off"}
              </p>
              <p className="mt-2 max-w-md text-sm text-slate-300">
                {cameraOn
                  ? "The dashboard stream is ready. Check that ROS is publishing /camera/image_raw from /dev/video2 if the image does not appear."
                  : "Switch on the camera when you want the live Jupiter webcam output to appear here."}
              </p>
              {!cameraOn && (
                <button
                  onClick={toggleCamera}
                  disabled={loadingAction === "camera"}
                  className="mt-5 inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 shadow-sm hover:bg-slate-100 disabled:opacity-60"
                  type="button"
                >
                  <Power className="h-4 w-4" />
                  Switch On Camera
                </button>
              )}
            </div>
          )}

          {cameraOn && frameAvailable && (
            <div className="absolute left-4 top-4 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-950/70 px-3 py-1.5 text-xs font-medium text-white ring-1 ring-white/15 backdrop-blur">
                <Circle className="h-2.5 w-2.5 fill-emerald-400 text-emerald-400" />
                Live camera
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-950/70 px-3 py-1.5 text-xs font-medium text-white ring-1 ring-white/15 backdrop-blur">
                <Eye className="h-3.5 w-3.5" />
                {visionModelOn ? "Emotion recognition on" : "Camera only"}
              </span>
            </div>
          )}
        </div>

        <div className="flex flex-col justify-between gap-5 bg-slate-950/25 p-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-300/70">Live status</p>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">Camera stream</dt>
                <dd className="font-medium text-white">{cameraOn ? "On" : "Off"}</dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">ROS topic</dt>
                <dd className="font-medium text-white">{vision.camera_topic}</dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">Frames</dt>
                <dd className="font-medium text-white">{frameAvailable ? "Receiving" : "Not detected"}</dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">Vision model</dt>
                <dd className="font-medium text-white">{visionModelOn ? "Running" : "Off"}</dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">Emotion estimate</dt>
                <dd className="font-medium capitalize text-white">
                  {emotionLabel}
                </dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">Confidence</dt>
                <dd className="font-medium text-white">
                  {visionModelOn && emotionConfidence > 0 ? `${Math.round(emotionConfidence * 100)}%` : "—"}
                </dd>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-white/[0.08] px-4 py-3 ring-1 ring-white/15">
                <dt className="text-slate-300/70">Emotion source</dt>
                <dd className="font-medium text-white">{visionModelOn ? emotionSource : "—"}</dd>
              </div>
            </dl>
          </div>

          <div className="rounded-2xl border border-white/15 bg-white/[0.08] p-4 text-sm text-slate-300/80">
            <p className="font-medium text-white">SmolVLM reading</p>
            <p className="mt-1">
              {analysisError
                ? `Vision model issue: ${analysisError}`
                : analysisDescription || "Switch on the Vision Module to show the model's latest visual reasoning here."}
            </p>
          </div>

          <div className="rounded-2xl border border-white/15 bg-white/[0.08] p-4 text-sm text-slate-300/80">
            <p className="font-medium text-white">Operator note</p>
            <p className="mt-1">
              Use <span className="font-medium text-white">Camera On</span> for normal monitoring. Enable the <span className="font-medium text-white">Vision Module</span> only when you want JUNO to run SmolVLM emotion recognition on the camera frames. Speech emotion cues still take priority when the user explicitly says how they feel.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

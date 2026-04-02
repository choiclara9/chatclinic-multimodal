"use client";

import { useEffect, useRef, useState } from "react";

interface NiivueViewerProps {
  niftiUrl: string;
}

export default function NiivueViewer({ niftiUrl }: NiivueViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nvRef = useRef<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [sliceType, setSliceType] = useState<number>(4); // multiplanar

  useEffect(() => {
    if (!canvasRef.current || !niftiUrl) return;

    let cancelled = false;

    async function init() {
      try {
        // Dynamic import — Niivue uses WebGL which is browser-only
        const niivueModule = await import("@niivue/niivue");
        const { Niivue } = niivueModule;

        if (cancelled || !canvasRef.current) return;

        const nv = new Niivue({
          backColor: [0.15, 0.15, 0.15, 1],
          show3Dcrosshair: true,
          multiplanarForceRender: true,
        });

        nv.attachToCanvas(canvasRef.current);

        await nv.loadVolumes([{ url: niftiUrl }]);

        nv.setSliceType(4); // multiplanar ACS + render
        nvRef.current = nv;
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      nvRef.current = null;
    };
  }, [niftiUrl]);

  useEffect(() => {
    if (nvRef.current) {
      try {
        nvRef.current.setSliceType(sliceType);
      } catch {
        // ignore
      }
    }
  }, [sliceType]);

  if (error) {
    return <p className="errorText">Niivue could not be loaded: {error}</p>;
  }

  return (
    <div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
        <button className={`pill ${sliceType === 0 ? "pillActive" : ""}`} onClick={() => setSliceType(0)}>Axial</button>
        <button className={`pill ${sliceType === 1 ? "pillActive" : ""}`} onClick={() => setSliceType(1)}>Coronal</button>
        <button className={`pill ${sliceType === 2 ? "pillActive" : ""}`} onClick={() => setSliceType(2)}>Sagittal</button>
        <button className={`pill ${sliceType === 4 ? "pillActive" : ""}`} onClick={() => setSliceType(4)}>Multi-planar</button>
        <button className={`pill ${sliceType === 3 ? "pillActive" : ""}`} onClick={() => setSliceType(3)}>3D Render</button>
      </div>
      <canvas
        ref={canvasRef}
        style={{ width: "100%", height: "450px", borderRadius: "6px", border: "1px solid var(--border-color, #ddd)" }}
      />
    </div>
  );
}

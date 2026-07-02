"use client";

import { useEffect, useState } from "react";

interface StreamedProfileState<T> {
  data: T | null;
  connected: boolean;
  done: boolean;
  error: Error | null;
}

function setNested<T>(target: T, path: string, value: unknown): T {
  const keys = path.split(".");
  const root: Record<string, unknown> = { ...(target as Record<string, unknown>) };
  let node = root;
  for (const key of keys.slice(0, -1)) {
    node[key] = { ...(node[key] as Record<string, unknown>) };
    node = node[key] as Record<string, unknown>;
  }
  node[keys[keys.length - 1]] = value;
  return root as T;
}

export function useStreamedProfile<T>(url: string): StreamedProfileState<T> {
  const [data, setData] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const es = new EventSource(url);

    es.addEventListener("base", (event) => {
      setData(JSON.parse((event as MessageEvent).data));
      setConnected(true);
    });

    es.addEventListener("field", (event) => {
      const { path, value } = JSON.parse((event as MessageEvent).data);
      setData((prev) => (prev ? setNested(prev, path, value) : prev));
    });

    es.addEventListener("done", () => {
      setDone(true);
      es.close();
    });

    es.onerror = () => {
      setError(new Error("stream connection error"));
      es.close();
    };

    return () => {
      es.close();
    };
  }, [url]);

  return { data, connected, done, error };
}

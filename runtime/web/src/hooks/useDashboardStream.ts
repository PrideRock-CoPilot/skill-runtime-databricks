import { useEffect } from "react";

import { getDashboardStreamUrl } from "../api";
import type { DashboardResponse } from "../types";

interface UseDashboardStreamArgs {
  sessionId: string;
  userId: string;
  onDashboard: (dashboard: DashboardResponse) => void;
  onError: (message: string) => void;
  onConnectionChange: (connected: boolean) => void;
}

export function useDashboardStream({ sessionId, userId, onDashboard, onError, onConnectionChange }: UseDashboardStreamArgs) {
  useEffect(() => {
    const streamUrl = getDashboardStreamUrl(sessionId, userId);
    const source = new EventSource(streamUrl);

    source.onopen = () => {
      onConnectionChange(true);
    };

    source.addEventListener("dashboard", (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent<string>).data) as DashboardResponse;
        onDashboard(payload);
      } catch {
        onError("Failed to parse live dashboard update.");
      }
    });

    source.onerror = () => {
      onConnectionChange(false);
    };

    return () => {
      source.close();
      onConnectionChange(false);
    };
  }, [sessionId, userId, onDashboard, onConnectionChange, onError]);
}

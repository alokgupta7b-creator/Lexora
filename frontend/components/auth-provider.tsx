"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

declare global {
  interface Window {
    __fetch_intercepted__?: boolean;
  }
}

export default function AuthProvider() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined" || window.__fetch_intercepted__) {
      return;
    }

    window.__fetch_intercepted__ = true;
    const originalFetch = window.fetch;

    window.fetch = async function (input, init) {
      let url = "";
      if (typeof input === "string") {
        url = input;
      } else if (input && typeof input === "object" && "url" in input) {
        url = input.url;
      } else if (input && typeof input === "object" && "toString" in input) {
        url = input.toString();
      }

      const isBackendUrl = url.startsWith("http://localhost:8000");

      if (isBackendUrl) {
        init = init || {};
        
        // 1. Force credentials: "include" to enable HttpOnly refresh cookies across origins
        init.credentials = "include";

        // 2. Auto-inject Authorization Bearer header if stored token exists and not already provided
        const storedToken = localStorage.getItem("token");
        if (storedToken) {
          init.headers = init.headers || {};
          
          if (init.headers instanceof Headers) {
            if (!init.headers.has("Authorization")) {
              init.headers.set("Authorization", `Bearer ${storedToken}`);
            }
          } else if (Array.isArray(init.headers)) {
            const hasAuth = init.headers.some(([k]) => k.toLowerCase() === "authorization");
            if (!hasAuth) {
              init.headers.push(["Authorization", `Bearer ${storedToken}`]);
            }
          } else {
            const headersObj = init.headers as Record<string, string>;
            if (!headersObj["Authorization"]) {
              headersObj["Authorization"] = `Bearer ${storedToken}`;
            }
          }
        }
      }

      // Execute original fetch
      let response = await originalFetch(input, init);

      // 3. Intercept HTTP 401 Unauthorized to trigger silent token rotation
      const isAuthRoute = url.includes("/auth/refresh") || url.includes("/auth/login") || url.includes("/auth/register");
      
      if (response.status === 401 && isBackendUrl && !isAuthRoute) {
        try {
          // Request access token refresh
          const refreshResp = await originalFetch("http://localhost:8000/api/v1/auth/refresh", {
            method: "POST",
            credentials: "include",
          });

          if (refreshResp.ok) {
            const refreshData = await refreshResp.json();
            localStorage.setItem("token", refreshData.access_token);

            // Re-apply headers and retry the original request
            init = init || {};
            init.headers = init.headers || {};
            
            if (init.headers instanceof Headers) {
              init.headers.set("Authorization", `Bearer ${refreshData.access_token}`);
            } else if (Array.isArray(init.headers)) {
              const idx = init.headers.findIndex(([k]) => k.toLowerCase() === "authorization");
              if (idx !== -1) {
                init.headers[idx][1] = `Bearer ${refreshData.access_token}`;
              } else {
                init.headers.push(["Authorization", `Bearer ${refreshData.access_token}`]);
              }
            } else {
              const headersObj = init.headers as Record<string, string>;
              headersObj["Authorization"] = `Bearer ${refreshData.access_token}`;
            }

            // Retry the original request
            response = await originalFetch(input, init);
          } else {
            // Refresh token has expired or is revoked - force log out
            localStorage.removeItem("token");
            localStorage.removeItem("userEmail");
            localStorage.removeItem("userRole");
            
            if (window.location.pathname !== "/login") {
              router.push("/login");
            }
          }
        } catch (err) {
          console.error("Critical: Global fetch interceptor failed during session refresh:", err);
        }
      }

      return response;
    };

    return () => {
      // Keep interceptor running for lifecycle duration
    };
  }, [router]);

  return null; // Logic-only wrapper
}

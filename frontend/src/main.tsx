import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { SWRConfig } from "swr";

import { App } from "@/App";
import { fetcher } from "@/lib/api";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <SWRConfig
      value={{
        fetcher,
        // Daily-tracking dashboard — no need for aggressive revalidation.
        // Re-fetch when the tab regains focus (user comes back to the page)
        // but skip the noisy 30s default polling.
        revalidateOnFocus: true,
        revalidateOnReconnect: true,
        refreshInterval: 0,
        // Surface fetch errors as console warnings rather than throwing in
        // render. The components show their own empty/error states.
        onError: (err) => console.warn("[swr]", err),
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </SWRConfig>
  </React.StrictMode>
);

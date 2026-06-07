import { useEffect, useRef, useState } from "react";
import { CheckCircle2, RefreshCcw, XCircle } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import { useToast } from "../../components/common/ToastProvider";
import { oaFormTextStyles } from "../../components/common/uiStyles";
import { exchangeUpstoxAuthCode } from "../../api/connectionApi";

function UpstoxCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const hasRunRef = useRef(false);

  const [pageStatus, setPageStatus] = useState("processing");
  const [message, setMessage] = useState("Processing Upstox authorization...");

  useEffect(() => {
    async function exchangeCode() {
      if (hasRunRef.current) {
        return;
      }

      hasRunRef.current = true;

      const code = searchParams.get("code");
      const error = searchParams.get("error");

      if (error) {
        setPageStatus("failed");
        setMessage(error);
        showToast(error, "error");
        return;
      }

      if (!code) {
        const errorMessage = "Authorization code not found in redirect URL.";

        setPageStatus("failed");
        setMessage(errorMessage);
        showToast(errorMessage, "error");
        return;
      }

      const usedCodeKey = `open_analytics_upstox_code_${code}`;

      if (sessionStorage.getItem(usedCodeKey)) {
        const successMessage = "Upstox access token already processed.";

        setPageStatus("success");
        setMessage(successMessage);
        showToast(successMessage, "success");

        window.setTimeout(() => {
          navigate("/connections", { replace: true });
        }, 1500);

        return;
      }

      sessionStorage.setItem(usedCodeKey, "1");

      try {
        const response = await exchangeUpstoxAuthCode({ code });
        const successMessage =
          response.data?.message || "Upstox access token generated successfully.";

        setPageStatus("success");
        setMessage(successMessage);
        showToast(successMessage, "success");

        window.setTimeout(() => {
          navigate("/connections", { replace: true });
        }, 3000);
      } catch (requestError) {
        sessionStorage.removeItem(usedCodeKey);

        const detail = requestError.response?.data?.detail;
        const errorMessage =
          typeof detail === "string"
            ? detail
            : detail?.message || "Unable to exchange Upstox authorization code.";

        setPageStatus("failed");
        setMessage(errorMessage);
        showToast(errorMessage, "error");
      }
    }

    exchangeCode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <MainLayout>
      <section className="relative min-h-screen bg-black p-3">
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-3">
          <div className="w-full max-w-sm rounded border border-oa-border bg-black p-6 text-center shadow-2xl">
            <div className="flex justify-center">
              {pageStatus === "processing" ? (
                <Spinner size="lg" color="light" />
              ) : null}

              {pageStatus === "success" ? (
                <CheckCircle2 size={46} className="text-emerald-300" />
              ) : null}

              {pageStatus === "failed" ? (
                <XCircle size={46} className="text-red-300" />
              ) : null}
            </div>

            <p className="mt-4 text-[14px] font-semibold text-white">
              {pageStatus === "processing"
                ? "Processing authorization"
                : pageStatus === "success"
                  ? "Authorization successful"
                  : "Authorization failed"}
            </p>

            <p className={`mt-2 ${oaFormTextStyles.helper}`}>{message}</p>

            {pageStatus === "success" ? (
              <p className="mt-3 text-[11px] text-oa-muted">
                Redirecting back to connections...
              </p>
            ) : null}

            {pageStatus === "failed" ? (
              <div className="mt-4 flex justify-center">
                <IconButton
                  icon={RefreshCcw}
                  label="Back to connections"
                  variant="default"
                  onClick={() => navigate("/connections", { replace: true })}
                  tooltipSide="top"
                />
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}

export default UpstoxCallback;
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState
} from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";

const ToastContext = createContext(null);

const toastStyles = {
  success: {
    icon: CheckCircle2,
    className: "border-emerald-500/40 bg-emerald-950/90 text-emerald-100",
    iconClassName: "text-emerald-300"
  },
  error: {
    icon: XCircle,
    className: "border-red-500/40 bg-red-950/90 text-red-100",
    iconClassName: "text-red-300"
  },
  warning: {
    icon: AlertTriangle,
    className: "border-amber-500/40 bg-amber-950/90 text-amber-100",
    iconClassName: "text-amber-300"
  },
  info: {
    icon: Info,
    className: "border-sky-500/40 bg-sky-950/90 text-sky-100",
    iconClassName: "text-sky-300"
  }
};

function ToastItem({ toast, onClose }) {
  const style = toastStyles[toast.type] || toastStyles.info;
  const Icon = style.icon;
  const isClosing = toast.closing === true;

  return (
    <div
      className={`flex min-h-10 w-[330px] max-w-[calc(100vw-24px)] items-start gap-2 rounded border px-3 py-2 text-xs shadow-2xl backdrop-blur ${style.className}`}
      style={{
        animation: isClosing
          ? "oaToastSlideOut 180ms ease-in forwards"
          : "oaToastSlideIn 220ms ease-out"
      }}
    >
      <Icon size={15} className={`mt-0.5 shrink-0 ${style.iconClassName}`} />

      <div className="min-w-0 flex-1">
        {toast.title && (
          <p className="mb-0.5 text-[12px] font-semibold text-white">
            {toast.title}
          </p>
        )}

        <p className="break-words text-[12px] leading-5">{toast.message}</p>
      </div>

      <button
        type="button"
        onClick={() => onClose(toast.id)}
        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-sm text-current opacity-70 transition hover:bg-black/30 hover:opacity-100"
        aria-label="Close notification"
      >
        <X size={13} />
      </button>
    </div>
  );
}

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((toastId) => {
    setToasts((previous) =>
      previous.map((toast) =>
        toast.id === toastId ? { ...toast, closing: true } : toast
      )
    );

    window.setTimeout(() => {
      setToasts((previous) => previous.filter((toast) => toast.id !== toastId));
    }, 190);
  }, []);

  const showToast = useCallback(
    (message, type = "info", options = {}) => {
      const toastId =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;

      const nextToast = {
        id: toastId,
        message,
        type,
        title: options.title || "",
        duration: options.duration ?? 3500,
        closing: false
      };

      setToasts((previous) => [...previous, nextToast]);

      if (nextToast.duration > 0) {
        window.setTimeout(() => {
          removeToast(toastId);
        }, nextToast.duration);
      }

      return toastId;
    },
    [removeToast]
  );

  const value = useMemo(
    () => ({
      showToast,
      removeToast
    }),
    [showToast, removeToast]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}

      <div className="fixed bottom-3 right-3 z-[11000] flex flex-col-reverse gap-2">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={removeToast} />
        ))}
      </div>

      <style>
        {`
          @keyframes oaToastSlideIn {
            from {
              opacity: 0;
              transform: translateX(28px);
            }
            to {
              opacity: 1;
              transform: translateX(0);
            }
          }

          @keyframes oaToastSlideOut {
            from {
              opacity: 1;
              transform: translateX(0);
            }
            to {
              opacity: 0;
              transform: translateX(28px);
            }
          }
        `}
      </style>
    </ToastContext.Provider>
  );
}

function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside ToastProvider.");
  }

  return context;
}

export { ToastProvider, useToast };

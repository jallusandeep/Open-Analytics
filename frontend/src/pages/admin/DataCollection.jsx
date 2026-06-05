import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Edit3,
  Play,
  Power,
  RefreshCcw,
  Search,
  Trash2,
  X,
  XCircle
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Select from "../../components/common/Select";
import Tooltip from "../../components/common/Tooltip";
import Modal from "../../components/common/Modal";
import DataTable from "../../components/tables/DataTable";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaFormTextStyles,
  oaPillStyles,
  oaTabStyles
} from "../../components/common/uiStyles";

import {
  cancelUpstoxDataCollection,
  createUpstoxDataCollectionSchedule,
  deleteUpstoxDataCollectionSchedule,
  getUpstoxDataCollectionRuns,
  getUpstoxDataCollectionSchedules,
  getUpstoxDataCollectionSummary,
  getUpstoxExpiredInstrumentsPreview,
  getUpstoxInstrumentsPreview,
  getUpstoxOHLCVPreview, // ✅ NEW
  syncUpstoxCurrentInstruments,
  syncUpstoxExpiredInstruments,
  toggleUpstoxDataCollectionSchedule,
  updateUpstoxDataCollectionSchedule
} from "../../api/dataCollectionApi";

const emptySummary = {
  connection_status: "not_connected",
  total_current_instruments: 0,
  total_expired_instruments: 0,
  total_sync_runs: 0,
  last_sync_at: "",
  last_duration_seconds: null,
  current_last_sync_at: "",
  current_duration_seconds: null,
  expired_last_sync_at: "",
  expired_duration_seconds: null,
  active_job: null,
  active_job_status: null,
  active_job_started_at: null,
  active_job_current_records: null,
  active_job_records_at_start: null,
  active_job_records_added: null
};

const emptyPreviewData = {
  rows: [],
  page: 1,
  page_size: 50,
  total_pages: 1,
  total_records: 0
};

const emptyScheduleForm = {
  schedule_id: "",
  job_type: "current_instruments",
  schedule_time: "",
  time_format: "24",
  is_active: true
};

const viewOptions = [
  { key: "monitor", label: "Collection Monitor" },
  { key: "current_preview", label: "Current Instruments" },
  { key: "expired_preview", label: "Expired Instruments" },
  { key: "ohlcv", label: "OHLCV" } // ✅ NEW TAB
];

const timeFormatOptions = [
  { value: "24", label: "24 Hours" },
  { value: "12", label: "12 Hours" }
];

const timePeriodOptions = [
  { value: "AM", label: "AM" },
  { value: "PM", label: "PM" }
];

const currentSourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "bod_complete", label: "BOD Complete" }
];

const expiredSourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "expired_option_contract", label: "Expired Options" },
  { value: "expired_future_contract", label: "Expired Futures" }
];

const segmentOptions = [
  { value: "all", label: "All Segments" },
  { value: "NSE_EQ", label: "NSE EQ" },
  { value: "BSE_EQ", label: "BSE EQ" },
  { value: "NSE_FO", label: "NSE FO" },
  { value: "BSE_FO", label: "BSE FO" },
  { value: "NSE_INDEX", label: "NSE Index" },
  { value: "BSE_INDEX", label: "BSE Index" },
  { value: "NCD_FO", label: "NCD FO" },
  { value: "BCD_FO", label: "BCD FO" }
];

const instrumentTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "EQ", label: "EQ" },
  { value: "FUT", label: "FUT" },
  { value: "CE", label: "CE" },
  { value: "PE", label: "PE" },
  { value: "INDEX", label: "INDEX" }
];

function getPreviewMode(activeView) {
  if (activeView === "expired_preview") return "expired";
  if (activeView === "ohlcv") return "ohlcv"; // ✅ NEW
  return "current";
}

function isPreviewView(activeView) {
  return activeView !== "monitor";
}

function DataCollection() {
  const [activeView, setActiveView] = useState("monitor");

  const [summary, setSummary] = useState(emptySummary);
  const [runs, setRuns] = useState([]);
  const [schedules, setSchedules] = useState([]);

  const [loading, setLoading] = useState(false);
  const [schedulerLoading, setSchedulerLoading] = useState(false);

  const [previewData, setPreviewData] = useState(emptyPreviewData);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [previewSearch, setPreviewSearch] = useState("");
  const [appliedPreviewSearch, setAppliedPreviewSearch] = useState("");
  const [previewSourceType, setPreviewSourceType] = useState("all");
  const [previewSegment, setPreviewSegment] = useState("all");
  const [previewInstrumentType, setPreviewInstrumentType] = useState("all");
  const [previewPage, setPreviewPage] = useState(1);

  const { showToast } = useToast();

  const isPreviewMode = isPreviewView(activeView);

  async function loadPreview(page = previewPage) {
    const mode = getPreviewMode(activeView);
    setPreviewLoading(true);

    try {
      const params = {
        search: appliedPreviewSearch,
        source_type: previewSourceType,
        segment: previewSegment,
        instrument_type: previewInstrumentType,
        page,
        page_size: 50
      };

      let response;

      if (mode === "expired") {
        response = await getUpstoxExpiredInstrumentsPreview(params);
      } else if (mode === "ohlcv") {
        response = await getUpstoxOHLCVPreview(params); // ✅ NEW
      } else {
        response = await getUpstoxInstrumentsPreview(params);
      }

      setPreviewData(response.data.data || response.data);
      setPreviewPage(page);
    } catch (e) {
      setPreviewData(emptyPreviewData);
      showToast("Failed to load preview data", "error");
    } finally {
      setPreviewLoading(false);
    }
  }

  function handleViewChange(view) {
    setActiveView(view);

    if (isPreviewView(view)) {
      setPreviewSearch("");
      setAppliedPreviewSearch("");
      setPreviewPage(1);
      setPreviewData(emptyPreviewData);
    }
  }

  useEffect(() => {
    if (isPreviewMode) {
      loadPreview(1);
    }
  }, [
    activeView,
    appliedPreviewSearch,
    previewSourceType,
    previewSegment,
    previewInstrumentType
  ]);

  return (
    <MainLayout>
      <div className="p-3 text-white">
        <div className={oaTabStyles.wrapper}>
          {viewOptions.map((v) => (
            <button
              key={v.key}
              onClick={() => handleViewChange(v.key)}
              className={`${oaTabStyles.button} ${activeView === v.key ? oaTabStyles.active : oaTabStyles.inactive
                }`}
            >
              {v.label}
            </button>
          ))}
        </div>

        {isPreviewMode && (
          <div className="mt-3">
            <DataTable
              columns={[
                { key: "instrument_key", label: "Instrument Key" },
                { key: "trading_symbol", label: "Symbol" },
                { key: "name", label: "Name" }
              ]}
              rows={previewData.rows}
              loading={previewLoading}
              getRowKey={(r, i) => i}
            />
          </div>
        )}
      </div>
    </MainLayout>
  );
}

export default DataCollection;
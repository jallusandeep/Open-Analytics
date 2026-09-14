import { oaPillStyles } from "../../../components/common/uiStyles";
import { StatusBadge } from "./components";
import {
  formatDateTime,
  formatPrice,
  formatNumber,
  getSyncTypeLabel,
  getOhlcvColumnValue,
  getMarketHolidayColumnValue,
  getEquityNewsColumnValue,
  getIpoCalendarColumnValue,
  getIpoScraperColumnValue,
  getCompanyFundamentalsColumnValue,
  formatJsonListCell
} from "./helpers";

export function renderOhlcvCell(row, column) {
  if (column.key === "source") {
    return (
      <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
        {getSyncTypeLabel(row.source)}
      </span>
    );
  }

  if (column.key === "mode") {
    return (
      <span className={`${oaPillStyles.base} border-sky-500/40 bg-sky-950/40 text-sky-200`}>
        {getSyncTypeLabel(row.mode)}
      </span>
    );
  }

  if (column.key === "interval_label") {
    return (
      <span className="truncate oa-code-font text-emerald-200">
        {row.interval_label || "--"}
      </span>
    );
  }

  if (column.key === "timestamp" || column.key === "ingested_at") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatDateTime(row[column.key])}
      </span>
    );
  }

  if (column.key === "date" || column.key === "expiry") {
    return (
      <span className="truncate oa-code-font text-cyan-200">
        {row[column.key] || "--"}
      </span>
    );
  }

  if (
    column.key === "open" ||
    column.key === "high" ||
    column.key === "low" ||
    column.key === "close"
  ) {
    return (
      <span className="truncate oa-code-font text-white">
        {formatPrice(row[column.key])}
      </span>
    );
  }

  if (column.key === "volume" || column.key === "open_interest") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatNumber(row[column.key] || 0)}
      </span>
    );
  }

  if (column.key === "trading_symbol") {
    return (
      <span className="truncate oa-code-font text-cyan-200">
        {row.trading_symbol || "--"}
      </span>
    );
  }

  if (column.key === "instrument_key") {
    return (
      <span className="truncate oa-code-font font-semibold text-white">
        {row.instrument_key || "--"}
      </span>
    );
  }

  return (
    <span className="truncate oa-code-font text-oa-muted">
      {getOhlcvColumnValue(row, column.key) || "--"}
    </span>
  );
}

export function renderMarketCalendarCell(row, column) {
  if (column.key === "holiday_date") {
    return (
      <span className="truncate oa-code-font font-semibold text-cyan-200">
        {row.holiday_date || "--"}
      </span>
    );
  }

  if (column.key === "description") {
    return <span className="truncate text-white">{row.description || "--"}</span>;
  }

  if (column.key === "holiday_type") {
    return (
      <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
        {getSyncTypeLabel(row.holiday_type)}
      </span>
    );
  }

  if (column.key === "is_trading_day") {
    return (
      <StatusBadge
        status={row.is_trading_day ? "active" : "inactive"}
        label={row.is_trading_day ? "Partially Open" : "Closed"}
      />
    );
  }

  if (column.key === "closed_exchanges") {
    return (
      <span className="truncate oa-code-font text-red-200">
        {formatJsonListCell(row.closed_exchanges)}
      </span>
    );
  }

  if (column.key === "open_exchanges") {
    return (
      <span className="truncate oa-code-font text-emerald-200">
        {formatJsonListCell(row.open_exchanges)}
      </span>
    );
  }

  if (column.key === "source_provider") {
    return (
      <span className={`${oaPillStyles.base} border-sky-500/40 bg-sky-950/40 text-sky-200`}>
        {getSyncTypeLabel(row.source_provider)}
      </span>
    );
  }

  if (column.key === "synced_at" || column.key === "updated_at") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatDateTime(row[column.key])}
      </span>
    );
  }

  return (
    <span className="truncate oa-code-font text-oa-muted">
      {getMarketHolidayColumnValue(row, column.key) || "--"}
    </span>
  );
}

export function renderEquityNewsCell(row, column) {
  if (column.key === "instrument_key") {
    return (
      <span className="truncate oa-code-font font-semibold text-white">
        {row.instrument_key || "--"}
      </span>
    );
  }

  if (column.key === "trading_symbol") {
    return (
      <span className="truncate oa-code-font text-cyan-200">
        {row.trading_symbol || "--"}
      </span>
    );
  }

  if (column.key === "company_name" || column.key === "heading") {
    return (
      <span className="truncate text-white">
        {getEquityNewsColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  if (column.key === "segment" || column.key === "source") {
    return (
      <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
        {getEquityNewsColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  if (column.key === "published_at" || column.key === "ingested_at") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatDateTime(row[column.key])}
      </span>
    );
  }

  if (column.key === "article_link") {
    const articleLink = getEquityNewsColumnValue(row, column.key);

    return articleLink ? (
      <a
        href={articleLink}
        target="_blank"
        rel="noreferrer"
        className="truncate oa-code-font text-sky-300 hover:text-sky-200"
      >
        {articleLink}
      </a>
    ) : (
      <span className="truncate oa-code-font text-oa-muted">--</span>
    );
  }

  return (
    <span className="truncate oa-code-font text-oa-muted">
      {getEquityNewsColumnValue(row, column.key) || "--"}
    </span>
  );
}

export function renderIpoCalendarCell(row, column) {
  if (column.key === "ipo_id" || column.key === "isin") {
    return (
      <span className="truncate oa-code-font font-semibold text-white">
        {row[column.key] || "--"}
      </span>
    );
  }

  if (column.key === "symbol") {
    return (
      <span className="truncate oa-code-font text-cyan-200">
        {row.symbol || "--"}
      </span>
    );
  }

  if (column.key === "name" || column.key === "industry") {
    return <span className="truncate text-white">{row[column.key] || "--"}</span>;
  }

  if (column.key === "status") {
    return <StatusBadge status={String(row.status || "").toLowerCase()} label={getSyncTypeLabel(row.status)} />;
  }

  if (column.key === "issue_type") {
    return (
      <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
        {getSyncTypeLabel(row.issue_type)}
      </span>
    );
  }

  if (column.key === "synced_at") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatDateTime(row.synced_at)}
      </span>
    );
  }

  if (
    column.key === "issue_size" ||
    column.key === "minimum_price" ||
    column.key === "maximum_price" ||
    column.key === "total_subscription"
  ) {
    return (
      <span className="truncate oa-code-font text-white">
        {formatPrice(row[column.key])}
      </span>
    );
  }

  return (
    <span className="truncate oa-code-font text-oa-muted">
      {getIpoCalendarColumnValue(row, column.key) || "--"}
    </span>
  );
}

export function renderIpoScraperCell(row, column) {
  if (column.key === "ipo_name") {
    return <span className="truncate text-white">{row.ipo_name || "--"}</span>;
  }

  if (column.key === "ipo_gmp") {
    return (
      <span className="truncate oa-code-font font-semibold text-emerald-200">
        {row.ipo_gmp || "--"}
      </span>
    );
  }

  if (column.key === "gain") {
    const isLoss = String(row.gain || "").includes("-");

    return (
      <span
        className={`truncate oa-code-font font-semibold ${
          isLoss ? "text-red-200" : "text-emerald-200"
        }`}
      >
        {row.gain || "--"}
      </span>
    );
  }

  if (column.key === "price_band" || column.key === "ipo_date") {
    return (
      <span className="truncate oa-code-font text-cyan-200">
        {row[column.key] || "--"}
      </span>
    );
  }

  if (column.key === "ipo_status") {
    return (
      <StatusBadge
        status={String(row.ipo_status || "").toLowerCase()}
        label={getSyncTypeLabel(row.ipo_status)}
      />
    );
  }

  if (column.key === "ipo_type") {
    return (
      <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
        {getSyncTypeLabel(row.ipo_type)}
      </span>
    );
  }

  if (column.key === "scraped_at" || column.key === "updated_at") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatDateTime(row[column.key])}
      </span>
    );
  }

  return (
    <span className="truncate oa-code-font text-oa-muted">
      {getIpoScraperColumnValue(row, column.key) || "--"}
    </span>
  );
}

export function renderCompanyFundamentalsCell(row, column) {
  if (column.key === "action_event_details") {
    return <span className="whitespace-normal text-oa-muted">{row.action_event_details || "--"}</span>;
  }

  if (column.key === "isin" || column.key === "instrument_key") {
    return (
      <span className="truncate oa-code-font font-semibold text-white">
        {row[column.key] || "--"}
      </span>
    );
  }

  if (column.key === "trading_symbol") {
    return (
      <span className="truncate oa-code-font text-cyan-200">
        {row.trading_symbol || "--"}
      </span>
    );
  }

  if (column.key === "company_name" || column.key === "sector") {
    return <span className="truncate text-white">{row[column.key] || "--"}</span>;
  }

  if (column.key === "endpoint_label") {
    return (
      <span className={`${oaPillStyles.base} border-sky-500/40 bg-sky-950/40 text-sky-200`}>
        {row.endpoint_label || getSyncTypeLabel(row.endpoint)}
      </span>
    );
  }

  if (column.key === "statement_type" || column.key === "time_period") {
    return (
      <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
        {getSyncTypeLabel(row[column.key])}
      </span>
    );
  }

  if (column.key === "api_status") {
    return <StatusBadge status={row.api_status || "idle"} />;
  }

  if (column.key === "synced_at") {
    return (
      <span className="truncate oa-code-font text-white">
        {formatDateTime(row.synced_at)}
      </span>
    );
  }

  if (column.key === "latest_period") {
    return (
      <span className="truncate oa-code-font text-emerald-200">
        {row.latest_period || "--"}
      </span>
    );
  }

  if (
    column.key === "latest_revenue" ||
    column.key === "latest_operating_profit" ||
    column.key === "latest_net_profit" ||
    column.key === "latest_total_asset" ||
    column.key === "latest_total_liability" ||
    column.key === "latest_operating_cash_flow" ||
    column.key === "pe_ratio_company" ||
    column.key === "pb_ratio_company" ||
    column.key === "roe_company" ||
    column.key === "roce_company"
  ) {
    return (
      <span className="truncate oa-code-font text-white">
        {formatPrice(row[column.key])}
      </span>
    );
  }

  if (
    column.key === "period_count" ||
    column.key === "item_count" ||
    column.key === "corporate_action_count" ||
    column.key === "competitor_count"
  ) {
    return (
      <span className="truncate oa-code-font text-white">
        {formatNumber(row[column.key] || 0)}
      </span>
    );
  }

  return (
    <span className="truncate oa-code-font text-oa-muted">
      {getCompanyFundamentalsColumnValue(row, column.key) ?? "--"}
    </span>
  );
}


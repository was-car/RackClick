import { reportUiWords } from './report-ui-words.ts';

// Read-only metadata only. Pending/error/action controls stay in their exporter.
export function ReportTechnicalDetails({ kind, lang, children }) {
  const words = reportUiWords[lang] || reportUiWords.en;
  return <details className="rc-report-technical" data-report-technical={kind}>
    <summary>{words.technical}</summary>
    {children}
  </details>;
}

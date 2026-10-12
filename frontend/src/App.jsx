import React, { useState } from "react";
import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";
import Footer from "./components/layout/Footer";
import Dashboard from "./pages/Dashboard";
import DatasetUpload from "./pages/DatasetUpload";
import PHIDetection from "./pages/PHIDetection";
import Anonymization from "./pages/Anonymization";
import ComplianceReport from "./pages/ComplianceReport";

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [file, setFile] = useState(null);
  const [anonymizationDone, setAnonymizationDone] = useState(false);
  const [reportDownloaded, setReportDownloaded] = useState(false);
  const [datasetsProcessed, setDatasetsProcessed] = useState(0); // placeholder
  const [apiResult, setApiResult] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [epsilon, setEpsilon] = useState(1.0);
  const [k, setK] = useState(3);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex">
        <Sidebar page={page} setPage={setPage} />

        <div className="flex-1 min-h-screen flex flex-col">
          <Header />

          <main className="flex-1 px-8 py-8 max-w-6xl w-full">
            {page === "dashboard" && (
              <Dashboard
                go={setPage}
                anonymizationDone={anonymizationDone}
                reportDownloaded={reportDownloaded}
                file={file}
                datasetsProcessed={datasetsProcessed}
                apiResult={apiResult}
              />
            )}
            {page === "upload" && <DatasetUpload file={file} setFile={setFile} setApiResult={setApiResult} go={setPage} />}
            {page === "detection" && <PHIDetection go={setPage} overrides={overrides} setOverrides={setOverrides} apiResult={apiResult} />}
            {page === "anonymization" && (
              <Anonymization
                go={setPage}
                applied={anonymizationDone}
                onApply={() => setAnonymizationDone(true)}
                epsilon={epsilon}
                setEpsilon={setEpsilon}
                k={k}
                setK={setK}
                apiResult={apiResult}
                setApiResult={setApiResult}
                overrides={overrides}
              />
            )}
            {page === "report" && (
              <ComplianceReport
                onDownload={() => setReportDownloaded(true)}
                file={file}
                overrides={overrides}
                anonymizationDone={anonymizationDone}
                go={setPage}
                epsilon={epsilon}
                k={k}
                apiResult={apiResult}
              />
            )}
            <Footer />
          </main>
        </div>
      </div>
    </div>
  );
}
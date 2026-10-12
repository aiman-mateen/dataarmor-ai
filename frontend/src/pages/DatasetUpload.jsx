import React, { useRef, useState } from "react";
import { Upload, File, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import ProgressBar from "../components/ui/ProgressBar";
import { detectPHI } from "../utils/api";

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DatasetUpload({ file, setFile, setApiResult, go }) {
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rawFile, setRawFile] = useState(null);
  const inputRef = useRef(null);

  const handleIncomingFile = (selectedFile) => {
    if (!selectedFile) return;
    setError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      const firstLine = String(e.target.result).split(/\r?\n/)[0] || "";
      const columnCount = firstLine ? firstLine.split(",").length : null;
      setFile({
        name: selectedFile.name,
        size: formatBytes(selectedFile.size),
        columns: columnCount,
      });
      setRawFile(selectedFile);
    };
    reader.readAsText(selectedFile.slice(0, 4096));
  };

  const handleUpload = async () => {
    if (!rawFile) return;
    setLoading(true);
    setError(null);

    try {
      const result = await detectPHI(rawFile);
      setApiResult(result);
      go("detection");
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Dataset Upload"
        description="Upload a healthcare dataset for automatic PHI detection and privacy preservation."
      />

      <Card className="p-8 max-w-2xl">
        <h3 className="text-base font-semibold text-slate-900 mb-1">
          Upload your CSV dataset
        </h3>
        <p className="text-sm text-slate-500 mb-6">
          Supported format: .csv, up to 50 MB.
        </p>

        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => handleIncomingFile(e.target.files?.[0])}
        />

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleIncomingFile(e.dataTransfer.files?.[0]);
          }}
          className={`rounded-xl border-2 border-dashed flex flex-col items-center justify-center text-center py-14 px-6 transition-colors ${
            dragOver ? "border-teal-500 bg-teal-50/50" : "border-slate-200 bg-slate-50"
          }`}
        >
          <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center mb-4">
            <Upload className="w-5 h-5 text-blue-800" strokeWidth={1.75} />
          </div>
          <p className="text-sm font-medium text-slate-700">
            Drag &amp; drop your file here
          </p>
          <p className="text-xs text-slate-400 mt-1 mb-5">or</p>
          <Button
            variant="primary"
            onClick={() => inputRef.current?.click()}
            disabled={loading}
          >
            <Upload className="w-4 h-4" />
            Choose File
          </Button>
        </div>

        {loading && (
          <div className="mt-6">
            <p className="text-sm text-slate-600 mb-2">
              Processing dataset — this may take a moment…
            </p>
            <ProgressBar value={70} variant="success" showLabel={false} />
            <p className="text-xs text-slate-400 mt-2">
              Running PHI detection across six ensemble models. This may take a few minutes depending on the dataset size.
            </p>
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {!loading && file && (
          <div className="mt-6 pt-6 border-t border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-teal-50 flex items-center justify-center">
                <File className="w-4 h-4 text-teal-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-800">{file.name}</p>
                <p className="text-xs text-slate-400">
                  {file.size}
                  {file.columns && ` · ${file.columns} columns detected`}
                </p>
              </div>
            </div>
            <CheckCircle2 className="w-5 h-5 text-teal-600" />
          </div>
        )}

        <Button
          variant="primary"
          className="w-full mt-6"
          disabled={!file || loading}
          onClick={handleUpload}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing…
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload and Analyze
            </>
          )}
        </Button>
      </Card>
    </div>
  );
}
import { useRef, useState } from "react";
import { uploadTender as uploadTenderApi } from "../api/api";

export default function TenderUpload() {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUploadTender = async () => {
    if (!file) {
      setStatus("Please select a tender PDF first.");
      return;
    }

    try {
      setLoading(true);
      setStatus("");
      const res = await uploadTenderApi(file);
      const message = res.data?.message || "Tender uploaded successfully.";
      const chunkCount = res.data?.details?.chunks;
      setStatus(
        typeof chunkCount === "number"
          ? `${message} Chunks: ${chunkCount}`
          : message
      );
    } catch (error) {
      setStatus(
        error?.response?.data?.detail ||
          "Tender upload failed. Check backend logs."
      );
    } finally {
      setLoading(false);
    }
  };

  const onUploadClick = () => {
    void handleUploadTender();
  };

  const onSelectFileClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-3">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(e) => {
          const selected = e.target.files?.[0] || null;
          setFile(selected);
          setStatus(selected ? `Selected: ${selected.name}` : "");
        }}
      />

      <button
        type="button"
        onClick={onSelectFileClick}
        className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg w-full border border-gray-500"
      >
        {file ? "Change Tender File" : "Select Tender PDF"}
      </button>

      <p className="text-xs text-gray-400">
        {file ? file.name : "No file selected"}
      </p>

      <button
        type="button"
        onClick={onUploadClick}
        disabled={loading}
        className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg w-full"
      >
        {loading ? "Uploading..." : "Upload Tender"}
      </button>

      {status && <p className="text-sm text-gray-300">{status}</p>}

    </div>
  );
}

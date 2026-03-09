import { useRef, useState } from "react";
import { uploadResume as uploadResumeApi } from "../api/api";

export default function ResumeUpload() {
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUploadResume = async () => {
    if (!file) {
      setStatus("Please select a resume PDF first.");
      return;
    }

    try {
      setLoading(true);
      setStatus("");
      const res = await uploadResumeApi(file);
      const resumeId = res.data?.resume_id;
      setStatus(
        resumeId
          ? `Resume uploaded successfully (ID: ${resumeId})`
          : "Resume uploaded successfully."
      );
    } catch (error) {
      setStatus(
        error?.response?.data?.detail ||
          "Resume upload failed. Check backend logs."
      );
    } finally {
      setLoading(false);
    }
  };

  const onUploadClick = () => {
    void handleUploadResume();
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
        {file ? "Change Resume File" : "Select Resume PDF"}
      </button>

      <p className="text-xs text-gray-400">
        {file ? file.name : "No file selected"}
      </p>

      <button
        type="button"
        onClick={onUploadClick}
        disabled={loading}
        className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg w-full"
      >
        {loading ? "Uploading..." : "Upload Resume"}
      </button>

      {status && <p className="text-sm text-gray-300">{status}</p>}

    </div>
  );
}

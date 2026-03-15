import { useState } from "react";
import API from "./api/api";
import ResumeUpload from "./components/ResumeUpload";
import TenderUpload from "./components/TenderUpload";
import AskAgent from "./components/AskAgent";

function App() {
  const [activeResumeDocumentIds, setActiveResumeDocumentIds] = useState([]);
  const [activeTenderDocumentId, setActiveTenderDocumentId] = useState(null);
  const [uiResetKey, setUiResetKey] = useState(0);
  const [systemMessage, setSystemMessage] = useState("");
  const [systemMessageIsError, setSystemMessageIsError] = useState(false);
  const [clearingDatabase, setClearingDatabase] = useState(false);

  const clearDatabase = async () => {
    const confirmed = window.confirm(
      "This will delete all stored tenders, resumes, vectors, and extracted data. Continue?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setClearingDatabase(true);
      setSystemMessage("");
      setSystemMessageIsError(false);

      const res = await API.post("/system/clear-database");

      setActiveResumeDocumentIds([]);
      setActiveTenderDocumentId(null);
      setUiResetKey((value) => value + 1);
      setSystemMessage(res.data?.message || "Application database cleared successfully.");
    } catch (error) {
      console.error(error);
      setSystemMessageIsError(true);
      setSystemMessage("Failed to clear application database.");
      alert("Database clear failed");
    } finally {
      setClearingDatabase(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="bg-gray-800 border-b border-gray-700 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Tender AI Matching System</h1>
            <p className="text-gray-400 mt-1">
              Upload tender PDF, upload one or many resumes, and find the best candidates.
            </p>
            {systemMessage && (
              <p className={`mt-3 text-sm ${systemMessageIsError ? "text-red-300" : "text-green-300"}`}>
                {systemMessage}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={clearDatabase}
            disabled={clearingDatabase}
            className="rounded-lg border border-red-400 bg-transparent px-4 py-3 text-red-300 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {clearingDatabase ? "Clearing..." : "Clear Database"}
          </button>
        </div>
      </div>

      <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-xl p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Upload Resumes</h2>
          <ResumeUpload
            key={`resume-${uiResetKey}`}
            onUploadComplete={setActiveResumeDocumentIds}
          />
        </div>

        <div className="bg-gray-800 rounded-xl p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Upload Tender</h2>
          <TenderUpload
            key={`tender-${uiResetKey}`}
            onUploadComplete={setActiveTenderDocumentId}
          />
        </div>

        <div className="bg-gray-800 rounded-xl p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Ask AI</h2>
          <AskAgent
            key={`ask-${uiResetKey}`}
            activeResumeDocumentIds={activeResumeDocumentIds}
            activeTenderDocumentId={activeTenderDocumentId}
          />
        </div>
      </div>
    </div>
  );
}

export default App;

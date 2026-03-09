import { useState } from "react";
import { matchResumes } from "../api/api";

export default function AskAgent() {
  const [tenderText, setTenderText] = useState("");
  const [matches, setMatches] = useState([]);
  const [requirements, setRequirements] = useState(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const askAI = async () => {
    if (!tenderText.trim()) {
      setStatus("Please enter tender requirements.");
      return;
    }

    try {
      setLoading(true);
      setStatus("");
      const res = await matchResumes(tenderText);
      const topLevelMatches = res.data?.matches;
      const nestedMatches = topLevelMatches?.matches;
      const list = Array.isArray(topLevelMatches)
        ? topLevelMatches
        : Array.isArray(nestedMatches)
          ? nestedMatches
          : [];
      const extractedRequirements = topLevelMatches?.tender_requirements || null;

      setMatches(list);
      setRequirements(extractedRequirements);
      setStatus(
        list.length ? `Found ${list.length} matching resume chunks.` : "No matches found."
      );
    } catch (error) {
      setStatus(
        error?.response?.data?.detail || "Matching failed. Check backend logs."
      );
      setMatches([]);
      setRequirements(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <textarea
        className="w-full p-2 rounded bg-gray-700 border border-gray-600 min-h-28"
        placeholder="Paste tender requirements here..."
        value={tenderText}
        onChange={(e) => setTenderText(e.target.value)}
      />

      <button
        type="button"
        onClick={askAI}
        disabled={loading}
        className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg w-full"
      >
        {loading ? "Matching..." : "Find Matches"}
      </button>

      {status && <p className="text-sm text-gray-300">{status}</p>}

      {requirements && (
        <div className="bg-gray-700 p-3 rounded-lg mt-2 text-sm">
          <p className="font-semibold mb-1">Extracted Requirements</p>
          <p>
            Skills:{" "}
            {requirements.skills_required?.length
              ? requirements.skills_required.join(", ")
              : "None detected"}
          </p>
          <p>
            Experience: {requirements.experience_required || "Not detected"}
          </p>
        </div>
      )}

      {!!matches.length && (
        <div className="bg-gray-700 p-3 rounded-lg mt-3 space-y-2">
          {matches.map((match, idx) => (
            <div key={idx} className="text-sm border-b border-gray-600 pb-2 last:border-b-0">
              {typeof match === "string" ? (
                match
              ) : (
                <div className="space-y-1">
                  <p className="font-semibold">Score: {match.score}%</p>
                  <p>
                    Matched Skills:{" "}
                    {match.matched_skills?.length
                      ? match.matched_skills.join(", ")
                      : "None"}
                  </p>
                  <p className="text-gray-300">
                    {match.resume_excerpt || "No excerpt available"}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

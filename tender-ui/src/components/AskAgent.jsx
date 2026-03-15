import { useState } from "react";
import API from "../api/api";

export default function AskAgent({
  activeResumeDocumentIds = [],
  activeTenderDocumentId = null,
  onAnswerReady,
}) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchRankedProfiles = async () => {
    if (!activeTenderDocumentId || !activeResumeDocumentIds.length) {
      return null;
    }

    const res = await API.post("/match/", {
      query: "shortlist top matching profiles for the uploaded tender",
      tender_document_id: activeTenderDocumentId,
      resume_document_ids: activeResumeDocumentIds,
      restrict_to_active_uploads: true,
    });

    return res.data?.matches || null;
  };

  const askAI = async () => {
    if (!query.trim()) {
      alert("Please enter a query");
      return;
    }

    try {
      setLoading(true);

      const res = await API.post("/match/", {
        query: query,
        tender_document_id: activeTenderDocumentId,
        resume_document_ids: activeResumeDocumentIds,
        restrict_to_active_uploads: true,
      });

      const answerPayload = res.data?.matches || null;
      setAnswer(answerPayload);

      let profilesPayload = answerPayload;
      const needsProfileFetch =
        answerPayload?.mode !== "matching" &&
        activeTenderDocumentId &&
        activeResumeDocumentIds.length > 0;

      if (needsProfileFetch) {
        try {
          const rankedProfiles = await fetchRankedProfiles();
          if (rankedProfiles) {
            profilesPayload = rankedProfiles;
          }
        } catch (profileError) {
          console.error(profileError);
        }
      }

      onAnswerReady?.(profilesPayload);
    } catch (error) {
      console.error(error);
      alert("Matching failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <textarea
        className="w-full p-3 rounded bg-gray-700 border border-gray-600"
        rows="4"
        placeholder="Ask about the uploaded tender, uploaded resumes, or ask for matching"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <button
        onClick={askAI}
        disabled={loading}
        className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 px-4 py-2 rounded-lg w-full"
      >
        {loading ? "Analyzing..." : "Ask AI"}
      </button>

      {answer && (
        <div className="bg-gray-700 p-4 rounded-lg text-sm space-y-4">
          {answer.message && <p><strong>{answer.message}</strong></p>}

          {answer.answer_text && (
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="font-semibold mb-2">Answer</p>
              <p>{answer.answer_text}</p>
            </div>
          )}

          {answer.sources?.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="font-semibold mb-2">Sources</p>
              <ul className="space-y-1">
                {answer.sources.map((source, index) => (
                  <li key={index}>
                    {source.filename} — page {source.page_start ?? "?"}
                    {source.page_end && source.page_end !== source.page_start ? `-${source.page_end}` : ""}
                    {source.section ? ` — ${source.section}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {answer.tender_requirements && (
            <div>
              <p className="font-semibold mb-2">Extracted Tender Requirements</p>
              <p>
                <strong>Skills:</strong>{" "}
                {answer.tender_requirements.skills_required?.length
                  ? answer.tender_requirements.skills_required.join(", ")
                  : "None detected"}
              </p>
              <p>
                <strong>Experience:</strong>{" "}
                {answer.tender_requirements.experience_required || "Not detected"} years
              </p>
            </div>
          )}

          {answer.tender_evidence_map && (
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="font-semibold mb-2">Tender Evidence</p>
              <p>
                <strong>Role Page:</strong>{" "}
                {answer.tender_evidence_map.role?.page ?? "Not detected"}
              </p>
              <p>
                <strong>Experience Page:</strong>{" "}
                {answer.tender_evidence_map.experience_required?.page ?? "Not detected"}
              </p>
            </div>
          )}

          {answer.reasoning_summary && (
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="font-semibold mb-2">Reasoning Summary</p>
              <p>{answer.reasoning_summary}</p>
            </div>
          )}

          {answer.matches?.length > 0 ? (
            <div className="space-y-4">
              <p className="font-semibold">Matching Resumes</p>

              {answer.matches.map((item, index) => (
                <div key={index} className="bg-gray-800 rounded-lg p-4 space-y-2">
                  <p><strong>Filename:</strong> {item.filename}</p>
                  <p><strong>Candidate Name:</strong> {item.candidate_name || "Not detected"}</p>
                  <p><strong>Candidate Role:</strong> {item.candidate_role || "Not detected"}</p>
                  <p><strong>Candidate Domain:</strong> {item.candidate_domain || "Not detected"}</p>
                  <p><strong>Score:</strong> {item.score}%</p>
                  <p><strong>Verdict:</strong> {item.verdict}</p>
                  <p><strong>Candidate Experience:</strong> {item.candidate_experience ?? "Not detected"} years</p>
                  <p><strong>Required Experience:</strong> {item.required_experience ?? "Not detected"} years</p>
                  <p><strong>Experience Match:</strong> {item.experience_match ? "Yes" : "No"}</p>
                  <p><strong>Role Match:</strong> {item.role_match ? "Yes" : "No"}</p>
                  <p><strong>Domain Match:</strong> {item.domain_match ? "Yes" : "No"}</p>
                  <p><strong>Matched Skills:</strong> {item.matched_skills?.length ? item.matched_skills.join(", ") : "None"}</p>
                  <p><strong>Matched Preferred Skills:</strong> {item.matched_preferred_skills?.length ? item.matched_preferred_skills.join(", ") : "None"}</p>
                  <p><strong>Missing Skills:</strong> {item.missing_skills?.length ? item.missing_skills.join(", ") : "None"}</p>
                  <p><strong>Reasoning:</strong> {item.reasoning}</p>
                  {item.candidate_evidence_map?.experience && (
                    <p><strong>Candidate Experience Evidence Page:</strong> {item.candidate_evidence_map.experience.page ?? "Not detected"}</p>
                  )}
                  <p><strong>Excerpt:</strong> {item.resume_excerpt}</p>
                </div>
              ))}
            </div>
          ) : answer.mode === "matching" ? (
            <p>No matches found.</p>
          ) : null}
        </div>
      )}
    </div>
  );
}

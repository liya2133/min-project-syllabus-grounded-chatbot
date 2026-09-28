import React from 'react';
import Sources from './Sources';

export default function AnswerBox({ result, isLoading, connectionError, generalError }) {
  if (isLoading) {
    return (
      <div className="card loading-card">
        <div className="spinner" />
        <p className="loading-text">Searching syllabus and generating answer...</p>
        <span className="loading-subtext">Checking syllabus materials and previous year questions</span>
      </div>
    );
  }

  if (connectionError) {
    return (
      <div className="card error-card">
        <div className="error-header">
          <span className="error-icon">⚠️</span>
          <h4>Connection Error</h4>
        </div>
        <p>{connectionError}</p>
        <span className="error-hint">Make sure Flask is running at <code>http://127.0.0.1:5000</code></span>
      </div>
    );
  }

  if (generalError) {
    return (
      <div className="card error-card">
        <div className="error-header">
          <span className="error-icon">⚠️</span>
          <h4>Error</h4>
        </div>
        <p>{generalError}</p>
      </div>
    );
  }

  if (!result) {
    return null;
  }

  // Check if topic is not covered in syllabus material
  const isNotCovered =
    result.answer &&
    (result.answer.includes("Sorry, this isn't covered in the material I have.") ||
      result.answer.toLowerCase().includes("not covered in the material") ||
      result.answer.toLowerCase().includes("isn't covered in the material") ||
      (result.sources?.length === 0 && result.answer.toLowerCase().includes("not covered")));

  const examRelevance = result.exam_relevance;
  const hasPYQs = examRelevance && examRelevance.found && examRelevance.questions?.length > 0;

  return (
    <div className="card answer-card">
      {isNotCovered ? (
        <div className="not-covered-banner">
          <div className="not-covered-badge">
            <span className="badge-icon">ℹ️</span> Notice
          </div>
          <p className="not-covered-message">
            This topic is not covered in the available study materials.
          </p>
        </div>
      ) : (
        <div className="answer-section">
          <h3 className="section-title">
            <span className="section-icon">💡</span> Answer
          </h3>
          <div className="answer-text">
            {result.answer.split('\n\n').map((paragraph, idx) => (
              <p key={idx}>{paragraph}</p>
            ))}
          </div>
        </div>
      )}

      {/* Referenced Sources */}
      {result.sources && result.sources.length > 0 && (
        <Sources sources={result.sources} />
      )}

      {/* Previous Year Questions (PYQs) Relevance */}
      {hasPYQs && (
        <div className="pyq-container">
          <div className="pyq-header">
            <h3 className="section-title">
              <span className="section-icon">📝</span> Previous Year Questions (PYQ Relevance)
            </h3>
            <span className="pyq-count-badge">
              {examRelevance.count || examRelevance.questions.length} Question{examRelevance.questions.length > 1 ? 's' : ''} Found
            </span>
          </div>

          <div className="pyq-list">
            {examRelevance.questions.map((pyq, index) => (
              <div key={index} className="pyq-card">
                <div className="pyq-meta">
                  {pyq.year && <span className="meta-tag year-tag">Year {pyq.year}</span>}
                  {pyq.question_number && (
                    <span className="meta-tag qnum-tag">
                      Q{pyq.question_number}{pyq.part ? ` (${pyq.part})` : ''}
                    </span>
                  )}
                  {pyq.marks !== null && pyq.marks !== undefined && (
                    <span className="meta-tag marks-tag">{pyq.marks} Marks</span>
                  )}
                  {pyq.module && <span className="meta-tag module-tag">{pyq.module}</span>}
                  {pyq.or_group && <span className="meta-tag or-tag">OR: {pyq.or_group}</span>}
                </div>
                <div className="pyq-text">{pyq.question_text}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

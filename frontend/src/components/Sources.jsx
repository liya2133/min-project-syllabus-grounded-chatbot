import React from 'react';

export default function Sources({ sources }) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="sources-container">
      <h3 className="section-title">
        <span className="section-icon">📚</span> Referenced Sources
      </h3>
      <div className="sources-list">
        {sources.map((src, index) => (
          <div key={index} className="source-card">
            <div className="source-doc">
              <span className="source-label">Document:</span>
              <span className="source-value">{src.filename || 'Unknown Document'}</span>
            </div>
            <div className="source-page">
              <span className="source-label">Page:</span>
              <span className="source-badge">
                {src.page_number !== null && src.page_number !== undefined
                  ? `Page ${src.page_number}`
                  : 'N/A'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

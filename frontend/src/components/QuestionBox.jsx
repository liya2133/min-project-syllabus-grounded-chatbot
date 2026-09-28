import React from 'react';

export default function QuestionBox({
  question,
  onChangeQuestion,
  onSubmit,
  isLoading,
  disabled
}) {
  const handleKeyDown = (e) => {
    // Submit on Ctrl+Enter or Cmd+Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!isLoading && question.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="form-group">
      <label htmlFor="question-input" className="form-label">
        Your Doubt / Question
      </label>
      <textarea
        id="question-input"
        className="form-textarea"
        rows="4"
        placeholder="Type your academic question here (e.g., What is supervised learning?)..."
        value={question}
        onChange={(e) => onChangeQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || isLoading}
      />
      <div className="form-actions">
        <span className="shortcut-hint">Tip: Press Ctrl + Enter to submit</span>
        <button
          type="button"
          className="btn-primary"
          onClick={onSubmit}
          disabled={disabled || isLoading || !question.trim()}
        >
          {isLoading ? (
            <>
              <span className="spinner-small" aria-hidden="true" />
              <span>Searching Syllabus...</span>
            </>
          ) : (
            'Ask Question'
          )}
        </button>
      </div>
    </div>
  );
}

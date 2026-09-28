import React from 'react';

export default function SubjectSelector({
  subjects,
  selectedSubject,
  onSelectSubject,
  isLoading,
  disabled
}) {
  return (
    <div className="form-group">
      <label htmlFor="subject-select" className="form-label">
        Subject
      </label>
      <div className="select-wrapper">
        <select
          id="subject-select"
          className="form-select"
          value={selectedSubject}
          onChange={(e) => onSelectSubject(e.target.value)}
          disabled={disabled || isLoading}
        >
          <option value="">-- All Subjects (Default) --</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
              {subject.code ? ` (${subject.code})` : ''}
              {subject.semester ? ` - Sem ${subject.semester}` : ''}
            </option>
          ))}
        </select>
        {isLoading && <span className="helper-text">Loading subjects...</span>}
      </div>
    </div>
  );
}

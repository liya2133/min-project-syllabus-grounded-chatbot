import React, { useState, useEffect } from 'react';
import SubjectSelector from './components/SubjectSelector';
import QuestionBox from './components/QuestionBox';
import AnswerBox from './components/AnswerBox';
import './App.css';

const API_BASE_URL = 'http://127.0.0.1:5000';

export default function App() {
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubjectsLoading, setIsSubjectsLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(null);
  const [generalError, setGeneralError] = useState(null);
  const [result, setResult] = useState(null);

  const fetchSubjects = async () => {
    setIsSubjectsLoading(true);
    setConnectionError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/subjects`);
      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }
      const data = await response.json();
      if (data && Array.isArray(data.subjects)) {
        setSubjects(data.subjects);
      } else {
        setSubjects([]);
      }
    } catch (err) {
      console.warn('Could not fetch subjects:', err);
      setConnectionError(
        'Unable to connect to the backend server. Please make sure the Flask backend is running on http://127.0.0.1:5000.'
      );
    } finally {
      setIsSubjectsLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAskQuestion = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    setIsLoading(true);
    setConnectionError(null);
    setGeneralError(null);
    setResult(null);

    const payload = {
      question: trimmedQuestion,
      subject_id: selectedSubject ? parseInt(selectedSubject, 10) : null,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        setGeneralError(data?.error || `Server error (${response.status})`);
        return;
      }

      setResult(data);
    } catch (err) {
      console.error('Error submitting question:', err);
      setConnectionError(
        'Unable to connect to the backend server. Please make sure the Flask backend is running on http://127.0.0.1:5000.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-badge">Student Portal</div>
        <h1 className="project-title">Syllabus-Grounded Doubt-Solving Chatbot</h1>
        <p className="project-subtitle">
          Ask questions directly grounded in your syllabus notes and verified with previous year exam questions.
        </p>
      </header>

      {/* Main Content Area */}
      <main className="app-main">
        <section className="card input-card">
          <SubjectSelector
            subjects={subjects}
            selectedSubject={selectedSubject}
            onSelectSubject={setSelectedSubject}
            isLoading={isSubjectsLoading}
            disabled={isLoading}
          />

          <QuestionBox
            question={question}
            onChangeQuestion={setQuestion}
            onSubmit={handleAskQuestion}
            isLoading={isLoading}
            disabled={isLoading}
          />
        </section>

        {/* Results & Feedback Section */}
        <section className="results-section">
          <AnswerBox
            result={result}
            isLoading={isLoading}
            connectionError={connectionError}
            generalError={generalError}
          />
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Syllabus-Grounded Doubt-Solving System &bull; Powered by RAG &amp; Gemini</p>
      </footer>
    </div>
  );
}

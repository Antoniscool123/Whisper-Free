import './styles.css';

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Whisper-Free</h1>
        <nav>
          <button>Home</button>
          <button>Record</button>
          <button>Files</button>
          <button>Settings</button>
        </nav>
      </aside>

      <main className="content">
        <h2>Dashboard</h2>
        <p>Free multilingual transcription.</p>

        <div className="actions">
          <button className="primary">Record Audio</button>
          <button>Open File</button>
        </div>

        <div className="card">
          <h3>Language</h3>
          <select>
            <option>Danish</option>
            <option>English</option>
          </select>
        </div>
      </main>
    </div>
  );
}

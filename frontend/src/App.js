import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [department, setDepartment] = useState("cardiology");
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    try {
      const res = await fetch("/stats");
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleUpload = async () => {
    if (!files.length) {
      setMessage("⚠️ Please select files");
      return;
    }

    setLoading(true);
    setMessage("");

    const formData = new FormData();
    formData.append("department", department);

    for (let f of files) {
      formData.append("files", f);
    }

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      setMessage(`✅ ${data.message} (${data.chunks_uploaded} chunks)`);
      fetchStats();
    } catch (err) {
      setMessage("❌ Upload failed");
    }

    setLoading(false);
  };

  return (
    <div className="container">
      <h1>📄 Document Upload System</h1>

      <div className="card">
        <h3>Upload Documents</h3>

        <select value={department} onChange={(e) => setDepartment(e.target.value)}>
          <option value="cardiology">Cardiology</option>
          <option value="dentist">Dentist</option>
          <option value="general-medicine">General Medicine</option>
          <option value="neurology">Neurology</option>
          <option value="pulmonology">Pulmonology</option>
        </select>

        <input
          type="file"
          multiple
          onChange={(e) => setFiles(e.target.files)}
        />

        <button onClick={handleUpload} disabled={loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>

        {message && <p className="message">{message}</p>}
      </div>

      <div className="card">
        <h3>📊 Department Stats</h3>

        <table>
          <thead>
            <tr>
              <th>Department</th>
              <th>Documents</th>
            </tr>
          </thead>
          <tbody>
            {stats.map((s, i) => (
              <tr key={i}>
                <td>{s.department}</td>
                <td>{s.documents}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
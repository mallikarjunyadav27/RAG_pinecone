import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  // Indexes and Namespaces state
  const [indexes, setIndexes] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState("");
  
  const [namespaces, setNamespaces] = useState([]);
  const [selectedNamespace, setSelectedNamespace] = useState("");
  
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Fetch indexes on mount
  const fetchIndexes = async () => {
    try {
      const res = await fetch("/indexes");
      const data = await res.json();
      if (data.indexes && data.indexes.length > 0) {
        setIndexes(data.indexes);
        setSelectedIndex(data.indexes[0]); // Set first as default
      }
    } catch (err) {
      console.error("Failed to fetch indexes:", err);
    }
  };

  // Fetch namespaces when index changes
  const fetchNamespaces = async (indexName) => {
    if (!indexName) return;
    try {
      const res = await fetch(`/namespaces/${indexName}`);
      const data = await res.json();
      if (data.namespaces && data.namespaces.length > 0) {
        setNamespaces(data.namespaces);
        setSelectedNamespace(data.namespaces[0]); // Set first as default
      }
    } catch (err) {
      console.error("Failed to fetch namespaces:", err);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const res = await fetch("/stats");
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  useEffect(() => {
    fetchIndexes();
    fetchStats();
  }, []);

  // When index changes, fetch its namespaces
  useEffect(() => {
    if (selectedIndex) {
      fetchNamespaces(selectedIndex);
    }
  }, [selectedIndex]);


  const handleUpload = async () => {
    if (!files.length) {
      setMessage("⚠️ Please select files");
      return;
    }

    if (!selectedNamespace) {
      setMessage("⚠️ Please select a namespace");
      return;
    }

    setLoading(true);
    setMessage("");

    const formData = new FormData();
    formData.append("index_name", selectedIndex);
    formData.append("namespaces", selectedNamespace);

    for (let f of files) {
      formData.append("files", f);
    }

    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (data.error) {
        setMessage(`❌ ${data.error}`);
      } else {
        setMessage(
          `✅ ${data.message} - Index: ${data.index}, Namespace: ${data.namespaces.join(
            ", "
          )} (${data.chunks_uploaded} chunks)`
        );
        setFiles([]);
        setSelectedNamespace(namespaces.length > 0 ? namespaces[0] : "");
        fetchStats();
      }
    } catch (err) {
      console.error("Upload error:", err);
      setMessage("❌ Upload failed");
    }

    setLoading(false);
  };

  return (
    <div className="container">
      <h1>📄 Document Upload System</h1>

      <div className="card">
        <h3>Upload Documents</h3>

        {/* Index Selection */}
        <div className="form-group">
          <label>📑 Select Index:</label>
          <select 
            value={selectedIndex} 
            onChange={(e) => setSelectedIndex(e.target.value)}
            className="form-select"
          >
            {indexes.map((idx) => (
              <option key={idx} value={idx}>
                {idx}
              </option>
            ))}
          </select>
        </div>

        {/* Namespace Single Select Dropdown */}
        <div className="form-group">
          <label>🏥 Select Namespace:</label>
          <select 
            value={selectedNamespace} 
            onChange={(e) => setSelectedNamespace(e.target.value)}
            className="form-select"
          >
            <option value="">-- Choose a namespace --</option>
            {namespaces.map((ns) => (
              <option key={ns} value={ns}>
                {ns.charAt(0).toUpperCase() + ns.slice(1).replace("-", " ")}
              </option>
            ))}
          </select>
        </div>

        {/* File Input */}
        <div className="form-group">
          <label>📁 Select Files (Multiple):</label>
          <input
            type="file"
            multiple
            onChange={(e) => setFiles(e.target.files)}
            className="file-input"
          />
        </div>

        {/* Upload Button */}
        <button 
          onClick={handleUpload} 
          disabled={loading}
          className="upload-btn"
        >
          {loading ? "⏳ Uploading..." : "🚀 Upload"}
        </button>

        {message && <p className="message">{message}</p>}
      </div>

      <div className="card">
        <h3>📊 Statistics</h3>

        <table>
          <thead>
            <tr>
              <th>Index</th>
              <th>Namespace</th>
              <th>Documents</th>
            </tr>
          </thead>
          <tbody>
            {stats.length > 0 ? (
              stats.map((s, i) => (
                <tr key={i}>
                  <td>{s.index}</td>
                  <td>{s.namespace}</td>
                  <td>{s.documents}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="3">No data available</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
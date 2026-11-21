import { useState, useEffect, useCallback } from 'react';
import './App.css';

const REASON_LABELS = {
  MISSING_IN_B: 'Missing in System B',
  ORPHAN_IN_B: 'Orphan in System B',
  DUPLICATE_IN_B: 'Duplicate in System B',
  VALUE_MISMATCH: 'Value Mismatch',
  LOCATION_MISMATCH: 'Location Mismatch',
  DATE_MISMATCH: 'Date Mismatch',
};

function formatCurrency(val) {
  if (val === null || val === undefined || val === '') {
    return '';
  }
  const num = parseFloat(val);
  if (isNaN(num)) return val;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num);
}

export default function App() {
  const [orgs, setOrgs] = useState(['ORG-A', 'ORG-B']);
  const [selectedOrg, setSelectedOrg] = useState('ORG-A');
  const [selectedReason, setSelectedReason] = useState('');
  const [sortKey, setSortKey] = useState('-value');
  const [disagreements, setDisagreements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load available orgs from API on mount
  useEffect(() => {
    fetch('/api/orgs/')
      .then((res) => (res.ok ? res.json() : ['ORG-A', 'ORG-B']))
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setOrgs(data);
          if (!data.includes(selectedOrg)) {
            setSelectedOrg(data[0]);
          }
        }
      })
      .catch(() => {
        // Fallback to defaults
      });
  }, []);

  const fetchDisagreements = useCallback(() => {
    if (!selectedOrg) return;
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    params.set('org', selectedOrg);
    if (selectedReason) {
      params.set('reason', selectedReason);
    }
    if (sortKey) {
      params.set('sort', sortKey);
    }

    fetch(`/api/disagreements/?${params.toString()}`)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((d) => {
            throw new Error(d.error || `HTTP error ${res.status}`);
          });
        }
        return res.json();
      })
      .then((data) => {
        setDisagreements(Array.isArray(data) ? data : data.disagreements || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedOrg, selectedReason, sortKey]);

  useEffect(() => {
    fetchDisagreements();
  }, [fetchDisagreements]);

  const handleSort = (field) => {
    if (sortKey === `-${field}`) {
      setSortKey(field);
    } else if (sortKey === field) {
      setSortKey(`-${field}`);
    } else {
      setSortKey(`-${field}`);
    }
  };

  const getSortIcon = (field) => {
    if (sortKey === `-${field}`) return ' ▼';
    if (sortKey === field) return ' ▲';
    return ' ↕';
  };

  return (
    <div className="container">
      <header className="header">
        <div className="title-section">
          <h1>DealerOS Reconciliation Ledger</h1>
          <p className="subtitle">
            Cross-system discrepancy detection between System A and System B with strict tenant isolation.
          </p>
        </div>

        <div className="controls-card">
          <div className="control-group">
            <label htmlFor="org-select">Organization (Tenant):</label>
            <select
              id="org-select"
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              className="select-input"
            >
              {orgs.map((org) => (
                <option key={org} value={org}>
                  {org}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="reason-filter">Filter by Reason:</label>
            <select
              id="reason-filter"
              value={selectedReason}
              onChange={(e) => setSelectedReason(e.target.value)}
              className="select-input"
            >
              <option value="">All Disagreements</option>
              {Object.entries(REASON_LABELS).map(([code, label]) => (
                <option key={code} value={code}>
                  {label} ({code})
                </option>
              ))}
            </select>
          </div>

          <button onClick={fetchDisagreements} className="btn-refresh" disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </header>

      {error && <div className="error-banner">Error: {error}</div>}

      <div className="table-meta">
        <span className="count-badge">
          Showing {disagreements.length} disagreement{disagreements.length === 1 ? '' : 's'} for <strong>{selectedOrg}</strong>
        </span>
        {selectedReason && (
          <span className="filter-pill">
            Filtered: {REASON_LABELS[selectedReason] || selectedReason}
            <button onClick={() => setSelectedReason('')} className="btn-clear-filter">✕</button>
          </span>
        )}
      </div>

      <div className="table-responsive">
        <table className="reconcile-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('reason')} className="sortable-th">
                Reason{getSortIcon('reason')}
              </th>
              <th onClick={() => handleSort('record_id')} className="sortable-th">
                Record ID{getSortIcon('record_id')}
              </th>
              <th onClick={() => handleSort('location')} className="sortable-th">
                Location{getSortIcon('location')}
              </th>
              <th>System A Value</th>
              <th onClick={() => handleSort('value')} className="sortable-th">
                System B Value{getSortIcon('value')}
              </th>
              <th onClick={() => handleSort('difference')} className="sortable-th">
                Difference{getSortIcon('difference')}
              </th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="text-center py-4">
                  Loading disagreements...
                </td>
              </tr>
            ) : disagreements.length === 0 ? (
              <tr>
                <td colSpan="7" className="empty-message">
                  No disagreements found for the selected criteria.
                </td>
              </tr>
            ) : (
              disagreements.map((row, idx) => (
                <tr key={`${row.record_id}-${row.reason}-${idx}`}>
                  <td>
                    <span className={`badge badge-${row.reason.toLowerCase()}`}>
                      {REASON_LABELS[row.reason] || row.reason}
                    </span>
                  </td>
                  <td className="font-mono font-bold">{row.record_id}</td>
                  <td>
                    <span className={row.location === '[EXTERNAL_LOCATION]' ? 'text-masked' : 'font-mono'}>
                      {row.location}
                    </span>
                  </td>
                  <td className="num-cell">
                    {row.a_value !== null && row.a_value !== undefined ? formatCurrency(row.a_value) : ''}
                  </td>
                  <td className="num-cell">
                    {row.b_value !== null && row.b_value !== undefined ? formatCurrency(row.b_value) : ''}
                  </td>
                  <td className="num-cell font-bold text-diff">
                    {row.difference !== null && row.difference !== undefined ? formatCurrency(row.difference) : ''}
                  </td>
                  <td className="text-details">{row.details}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

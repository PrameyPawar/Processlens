import React, { useEffect, useState } from 'react';

interface HealthData {
  status: string;
  service: string;
  version: string;
}

export const HealthStatus: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/health');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
          setError(false);
        } else {
          setError(true);
        }
      } catch (err) {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <span className="badge badge-warning">Checking backend...</span>;
  }

  if (error || !health) {
    return <span className="badge badge-danger">Backend Offline (Port 8000)</span>;
  }

  return (
    <span className="badge badge-success" title={`Service: ${health.service} v${health.version}`}>
      ● System Online (v{health.version})
    </span>
  );
};

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";

type Run = {
  id: string;
  supervisor_id: string;
  order_id: string;
  status: string;
  created_at: string;
};

type Supervisor = {
  id: string;
  name: string;
};

export default function Dashboard() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  
  // Form State
  const [selectedSupervisor, setSelectedSupervisor] = useState("");
  const [orderId, setOrderId] = useState("");
  const [orderContext, setOrderContext] = useState("{\n  \"customer_tier\": \"VIP\",\n  \"items\": [\"Laptop\"]\n}");

  useEffect(() => {
    fetchRuns();
    fetchSupervisors();
  }, []);

  const fetchRuns = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/runs");
      setRuns(res.data);
    } catch (e) {
      console.error("Failed to fetch runs", e);
    }
  };

  const fetchSupervisors = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/supervisors");
      setSupervisors(res.data);
      if (res.data.length > 0) setSelectedSupervisor(res.data[0].id);
    } catch (e) {
      console.error("Failed to fetch supervisors", e);
    }
  };

  const handleStartRun = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post("http://localhost:8000/api/runs", {
        supervisor_id: selectedSupervisor,
        order_id: orderId,
        order_context: JSON.parse(orderContext)
      });
      setIsModalOpen(false);
      fetchRuns();
    } catch (err) {
      alert("Invalid JSON context or backend error");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold tracking-tight">Order Runs</h1>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium text-sm transition-colors"
        >
          Start New Order Run
        </button>
      </div>

      <div className="bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Order ID</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              <th className="px-6 py-4 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {runs.map((run) => (
              <tr key={run.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{run.order_id}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                    run.status === 'running' ? 'bg-green-50 text-green-700 ring-green-600/20' : 
                    run.status === 'paused' ? 'bg-yellow-50 text-yellow-800 ring-yellow-600/20' :
                    'bg-gray-50 text-gray-600 ring-gray-500/10'
                  }`}>
                    {run.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(run.created_at).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <Link href={`/runs/${run.id}`} className="text-blue-600 hover:text-blue-900">
                    View Details
                  </Link>
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">
                  No order runs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/30 bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-lg font-semibold mb-4">Start New Order Run</h2>
            <form onSubmit={handleStartRun} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Supervisor Template</label>
                <select 
                  className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  value={selectedSupervisor}
                  onChange={(e) => setSelectedSupervisor(e.target.value)}
                  required
                >
                  {supervisors.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Order ID</label>
                <input 
                  type="text" 
                  className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  placeholder="ORD-12345"
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Order Context (JSON)</label>
                <textarea 
                  className="w-full border border-gray-300 rounded-md p-2 text-sm font-mono"
                  rows={4}
                  value={orderContext}
                  onChange={(e) => setOrderContext(e.target.value)}
                  required
                />
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
                >
                  Start Run
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

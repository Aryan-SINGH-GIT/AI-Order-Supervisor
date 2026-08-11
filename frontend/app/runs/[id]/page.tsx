"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import axios from "axios";

type RunDetails = {
  id: string;
  order_id: string;
  status: string;
  memory_summary: string;
  order_context: any;
  next_wake_up_at: string;
  activities: any[];
};

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const { id } = resolvedParams;
  
  const [run, setRun] = useState<RunDetails | null>(null);
  const [loading, setLoading] = useState(true);

  // Event Simulator State
  const [eventType, setEventType] = useState("order_created");
  const [eventPayload, setEventPayload] = useState("{}");
  const [instruction, setInstruction] = useState("");

  useEffect(() => {
    fetchRun();
    const interval = setInterval(fetchRun, 3000); // poll for updates
    return () => clearInterval(interval);
  }, [id]);

  const fetchRun = async () => {
    try {
      const res = await axios.get(`http://localhost:8000/api/runs/${id}`);
      setRun(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const sendAction = async (action: string) => {
    await axios.post(`http://localhost:8000/api/runs/${id}/${action}`);
    fetchRun();
  };

  const sendEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`http://localhost:8000/api/runs/${id}/events`, {
        event_type: eventType,
        payload: JSON.parse(eventPayload)
      });
      setEventType("order_created");
      setEventPayload("{}");
      fetchRun();
    } catch (err) {
      alert("Invalid JSON payload");
    }
  };

  const sendInstruction = async (e: React.FormEvent) => {
    e.preventDefault();
    await axios.post(`http://localhost:8000/api/runs/${id}/instructions`, {
      instruction
    });
    setInstruction("");
    fetchRun();
  };

  if (loading) return <div>Loading...</div>;
  if (!run) return <div>Run not found</div>;

  const isPaused = run.status === "paused";
  const isCompleted = run.status === "completed";

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <Link href="/" className="text-sm text-blue-600 hover:underline mb-2 inline-block">&larr; Back to Dashboard</Link>
          <h1 className="text-2xl font-bold tracking-tight">Run: {run.order_id}</h1>
          <div className="flex items-center space-x-3 mt-2 text-sm text-gray-500">
            <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
              run.status === 'running' ? 'bg-green-50 text-green-700 ring-green-600/20' : 
              run.status === 'paused' ? 'bg-yellow-50 text-yellow-800 ring-yellow-600/20' :
              'bg-gray-50 text-gray-600 ring-gray-500/10'
            }`}>
              {run.status.toUpperCase()}
            </span>
            {run.next_wake_up_at && <span>Next Wake: {new Date(run.next_wake_up_at).toLocaleString()}</span>}
          </div>
        </div>
        
        {!isCompleted && (
          <div className="flex space-x-2">
            <button 
              onClick={() => sendAction("interrupt")}
              className="bg-purple-100 text-purple-700 hover:bg-purple-200 px-3 py-1.5 rounded text-sm font-medium transition-colors"
            >
              Interrupt (Wake Now)
            </button>
            {isPaused ? (
              <button 
                onClick={() => sendAction("resume")}
                className="bg-green-100 text-green-700 hover:bg-green-200 px-3 py-1.5 rounded text-sm font-medium transition-colors"
              >
                Resume Workflow
              </button>
            ) : (
              <button 
                onClick={() => sendAction("pause")}
                className="bg-yellow-100 text-yellow-800 hover:bg-yellow-200 px-3 py-1.5 rounded text-sm font-medium transition-colors"
              >
                Pause Workflow
              </button>
            )}
            <button 
              onClick={() => sendAction("terminate")}
              className="bg-red-100 text-red-700 hover:bg-red-200 px-3 py-1.5 rounded text-sm font-medium transition-colors"
            >
              Terminate
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Timeline */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold border-b pb-2">Activity Timeline</h2>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="max-h-[600px] overflow-y-auto p-4 space-y-4">
              {run.activities?.map((act) => (
                <div key={act.id} className="flex space-x-3 text-sm">
                  <div className="text-gray-400 whitespace-nowrap pt-1 text-xs">
                    {new Date(act.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="flex-1 bg-gray-50 rounded-lg p-3 border border-gray-100">
                    <div className="font-semibold text-gray-900 mb-1 flex items-center justify-between">
                      <span>{act.name}</span>
                      <span className="text-[10px] uppercase tracking-wider text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                        {act.activity_type}
                      </span>
                    </div>
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono mt-2 bg-white p-2 rounded border border-gray-200">
                      {JSON.stringify(act.payload, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
              {(!run.activities || run.activities.length === 0) && (
                <div className="text-center text-gray-500 py-8">Waiting for activities...</div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Controls & Memory */}
        <div className="space-y-6">
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2 className="text-md font-semibold mb-3 border-b pb-2">Memory Summary</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {run.memory_summary || "No memory generated yet."}
            </p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <h2 className="text-md font-semibold mb-3 border-b pb-2">Order Context</h2>
            <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
              {JSON.stringify(run.order_context, null, 2)}
            </pre>
          </div>

          {!isCompleted && (
            <>
              <div className="bg-blue-50 rounded-xl shadow-sm border border-blue-100 p-5">
                <h2 className="text-md font-semibold mb-3 text-blue-900 border-b border-blue-200 pb-2">Add Manual Instruction</h2>
                <form onSubmit={sendInstruction} className="space-y-3">
                  <textarea 
                    className="w-full border border-blue-200 rounded-md p-2 text-sm focus:ring-blue-500 focus:border-blue-500 bg-white"
                    rows={2}
                    placeholder="e.g. Prioritize VIP shipping for this customer."
                    value={instruction}
                    onChange={e => setInstruction(e.target.value)}
                    required
                  />
                  <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md text-sm font-medium transition-colors">
                    Send Instruction
                  </button>
                </form>
              </div>

              <div className="bg-gray-50 rounded-xl shadow-sm border border-gray-200 p-5">
                <h2 className="text-md font-semibold mb-3 border-b pb-2">Event Simulator</h2>
                <form onSubmit={sendEvent} className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Event Type</label>
                    <select 
                      className="w-full border border-gray-300 rounded-md p-2 text-sm bg-white"
                      value={eventType}
                      onChange={e => setEventType(e.target.value)}
                    >
                      <option value="order_created">order_created</option>
                      <option value="payment_confirmed">payment_confirmed</option>
                      <option value="payment_failed">payment_failed</option>
                      <option value="shipment_created">shipment_created</option>
                      <option value="shipment_delayed">shipment_delayed</option>
                      <option value="delivered">delivered</option>
                      <option value="refund_requested">refund_requested</option>
                      <option value="customer_message_received">customer_message_received</option>
                      <option value="no_update_for_n_hours">no_update_for_n_hours</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Payload (JSON)</label>
                    <textarea 
                      className="w-full border border-gray-300 rounded-md p-2 text-sm font-mono bg-white"
                      rows={3}
                      value={eventPayload}
                      onChange={e => setEventPayload(e.target.value)}
                      required
                    />
                  </div>
                  <button type="submit" className="w-full bg-gray-800 hover:bg-gray-900 text-white py-2 rounded-md text-sm font-medium transition-colors">
                    Inject Event
                  </button>
                </form>
              </div>
            </>
          )}
          
        </div>
      </div>
    </div>
  );
}

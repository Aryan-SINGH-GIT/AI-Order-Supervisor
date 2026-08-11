"use client";

import { useEffect, useState } from "react";
import axios from "axios";

type SupervisorTemplate = {
  id: string;
  name: string;
  base_instruction: string;
  available_actions: string[];
  wake_aggressiveness: string;
  model_config: any;
  created_at: string;
};

const ALL_TOOLS = [
  "message_fulfillment_team",
  "message_payments_team",
  "message_logistics_team",
  "message_customer",
  "create_internal_note",
];

export default function SupervisorsPage() {
  const [supervisors, setSupervisors] = useState<SupervisorTemplate[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  const [name, setName] = useState("");
  const [instruction, setInstruction] = useState("");
  const [aggressiveness, setAggressiveness] = useState("medium");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  
  useEffect(() => {
    fetchSupervisors();
  }, []);

  const fetchSupervisors = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/supervisors");
      setSupervisors(res.data);
    } catch (e) {
      console.error("Failed to fetch", e);
    }
  };

  const toggleTool = (tool: string) => {
    if (selectedTools.includes(tool)) {
      setSelectedTools(selectedTools.filter(t => t !== tool));
    } else {
      setSelectedTools([...selectedTools, tool]);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post("http://localhost:8000/api/supervisors", {
        name: name,
        base_instruction: instruction,
        available_actions: selectedTools,
        wake_aggressiveness: aggressiveness,
        model_config: { model: "llama-3.3-70b-versatile" }
      });
      setIsModalOpen(false);
      fetchSupervisors();
      // Reset form
      setName(""); setInstruction(""); setAggressiveness("medium"); setSelectedTools([]);
    } catch (err) {
      alert("Error creating supervisor");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold tracking-tight">Supervisor Templates</h1>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium text-sm transition-colors"
        >
          Create Template
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {supervisors.map(s => (
          <div key={s.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-3">
            <div className="flex justify-between items-start">
              <h3 className="font-semibold text-lg">{s.name}</h3>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">{s.wake_aggressiveness}</span>
            </div>
            <p className="text-sm text-gray-600 line-clamp-3">{s.base_instruction}</p>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Available Actions</p>
              <div className="flex flex-wrap gap-1">
                {s.available_actions.map(action => (
                  <span key={action} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-md border border-blue-100">
                    {action}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
        {supervisors.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-500 border-2 border-dashed border-gray-200 rounded-xl">
            No supervisor templates configured yet.
          </div>
        )}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/30 bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <h2 className="text-lg font-semibold mb-4">Create Supervisor Template</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input 
                  type="text" 
                  className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base Instruction</label>
                <textarea 
                  className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  rows={3}
                  value={instruction}
                  onChange={e => setInstruction(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Wake Aggressiveness</label>
                <select 
                  className="w-full border border-gray-300 rounded-md p-2 text-sm"
                  value={aggressiveness}
                  onChange={e => setAggressiveness(e.target.value)}
                >
                  <option value="low">Low (Rarely wakes)</option>
                  <option value="medium">Medium (Standard)</option>
                  <option value="high">High (Wakes frequently)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Bind Actions to Agent</label>
                <div className="space-y-2">
                  {ALL_TOOLS.map(tool => (
                    <label key={tool} className="flex items-center space-x-2 text-sm cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={selectedTools.includes(tool)}
                        onChange={() => toggleTool(tool)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span>{tool}</span>
                    </label>
                  ))}
                </div>
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
                  Save Template
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

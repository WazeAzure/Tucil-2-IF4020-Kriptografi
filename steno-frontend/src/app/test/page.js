'use client';

import { useState } from 'react';

export default function TestPage() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const sendMessage = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResponse('');

    try {
      // Get backend URL from environment variable or use default
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
      
      const res = await fetch(`${backendUrl}/send-message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      const data = await res.json();

      if (data.success) {
        setResponse(data.response);
      } else {
        setError(data.error || 'Something went wrong');
      }
    } catch (err) {
      setError('Failed to connect to backend: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-8 max-w-md">
      <h1 className="text-2xl font-bold mb-6 text-center">Backend Test Page</h1>
      
      <form onSubmit={sendMessage} className="space-y-4">
        <div>
          <label htmlFor="message" className="block text-sm font-medium mb-2">
            Enter your message:
          </label>
          <input
            type="text"
            id="message"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Type your message here..."
            required
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:bg-blue-300 transition-colors"
        >
          {loading ? 'Sending...' : 'Send Message'}
        </button>
      </form>

      {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          <strong>Error:</strong> {error}
        </div>
      )}

      {response && (
        <div className="mt-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
          <strong>Response from backend:</strong>
          <p className="mt-1">{response}</p>
        </div>
      )}

      <div className="mt-6 text-sm text-gray-600">
        <p><strong>How it works:</strong></p>
        <ul className="list-disc list-inside mt-2 space-y-1">
          <li>Enter a message in the input field</li>
          <li>Click "Send Message" to send it to the Flask backend</li>
          <li>Backend prints the message to its terminal</li>
          <li>Backend appends " Ultra Marathon IRB" to your message</li>
          <li>Modified message is returned and displayed here</li>
        </ul>
      </div>
    </div>
  );
}

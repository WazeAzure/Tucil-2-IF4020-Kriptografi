"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Key, Download, Shuffle, FileText, Settings, Lock, Unlock } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState(null);
  const [embedFile, setEmbedFile] = useState(null);
  const [key, setKey] = useState("");
  const [outputFile, setOutputFile] = useState(null);
  const [useEncryption, setUseEncryption] = useState(true);
  const [randomEmbedding, setRandomEmbedding] = useState(false);
  const [lsbBits, setLsbBits] = useState(1);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === "audio/mpeg") {
      setSelectedFile(file);
    } else {
      alert("Please select an MP3 file");
      event.target.value = "";
    }
  };

  const handleEmbedFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setEmbedFile(file);
    }
  };

  const generateRandomKey = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let result = "";
    for (let i = 0; i < 25; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setKey(result);
  };

  const handleKeyChange = (event) => {
    const value = event.target.value;
    if (value.length <= 25) {
      setKey(value);
    }
  };

  const handleEmbedFile = () => {
    // This will be implemented when you add the API routes
    console.log("Embed file functionality to be implemented");
    console.log("Settings:", {
      mp3File: selectedFile?.name,
      embedFile: embedFile?.name,
      useEncryption,
      randomEmbedding,
      key: (useEncryption || randomEmbedding) ? key : null,
      lsbBits
    });
    // Simulating output for UI demonstration
    if (selectedFile && embedFile) {
      setOutputFile(selectedFile);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Audio Steganography Tool
          </h1>
          <p className="text-lg text-slate-600">
            Embed files securely into MP3 audio files
          </p>
          
          {/* Navigation Buttons */}
          <div className="flex justify-center gap-4 mt-8">
            <Button
              disabled={true}
              size="lg"
              className="px-6 py-2 bg-slate-700 text-white font-medium disabled:bg-slate-400 disabled:cursor-not-allowed"
            >
              <Lock className="w-4 h-4 mr-2" />
              Encrypt
            </Button>
            <Button
              onClick={() => router.push('/decrypt')}
              variant="outline"
              size="lg"
              className="px-6 py-2 border-slate-300 text-slate-700 hover:bg-slate-50"
            >
              <Unlock className="w-4 h-4 mr-2" />
              Decrypt
            </Button>
          </div>
        </div>

        {/* Main Container */}
        <div className="bg-white rounded-lg shadow-lg p-8 space-y-8">
          {/* File Input Section */}
          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Upload className="w-4 h-4" />
              Select MP3 File
            </label>
            <div className="relative">
              <input
                type="file"
                accept=".mp3,audio/mpeg"
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-3 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent"
              />
            </div>
            {selectedFile && (
              <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg">
                <strong>Selected:</strong> {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </div>
            )}
          </div>

          {/* File to Embed Section */}
          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <FileText className="w-4 h-4" />
              File to Embed
            </label>
            <div className="relative">
              <input
                type="file"
                onChange={handleEmbedFileChange}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-3 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent"
              />
            </div>
            {embedFile && (
              <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg">
                <strong>Selected:</strong> {embedFile.name} ({(embedFile.size / 1024).toFixed(2)} KB)
              </div>
            )}
          </div>

          {/* Options Section */}
          <div className="space-y-6 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Settings className="w-4 h-4" />
              Embedding Options
            </label>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Use Encryption Option */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-slate-900">Use Encryption</h4>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="encryption"
                      checked={useEncryption}
                      onChange={() => setUseEncryption(true)}
                      className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                    />
                    <span className="text-sm text-slate-700">Yes</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="encryption"
                      checked={!useEncryption}
                      onChange={() => setUseEncryption(false)}
                      className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                    />
                    <span className="text-sm text-slate-700">No</span>
                  </label>
                </div>
              </div>

              {/* n-LSB Option */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-slate-900">LSB Bits</h4>
                <select
                  value={lsbBits}
                  onChange={(e) => setLsbBits(parseInt(e.target.value))}
                  className="block w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent text-sm"
                >
                  <option value={1}>1-bit LSB</option>
                  <option value={2}>2-bit LSB</option>
                  <option value={3}>3-bit LSB</option>
                  <option value={4}>4-bit LSB</option>
                </select>
              </div>
            </div>

            {/* Random Embedding Point Option */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-slate-900">Random Embedding Point</h4>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="randomEmbedding"
                    checked={randomEmbedding}
                    onChange={() => setRandomEmbedding(true)}
                    className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                  />
                  <span className="text-sm text-slate-700">Yes</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="randomEmbedding"
                    checked={!randomEmbedding}
                    onChange={() => setRandomEmbedding(false)}
                    className="w-4 h-4 text-slate-600 border-slate-300 focus:ring-slate-500"
                  />
                  <span className="text-sm text-slate-700">No</span>
                </label>
              </div>
            </div>
          </div>

          {/* Key/Seed Input Section - Show when encryption or random embedding is enabled */}
          {(useEncryption || randomEmbedding) && (
            <div className="space-y-4">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Key className="w-4 h-4" />
                {useEncryption && randomEmbedding 
                  ? "Encryption Key & Randomization Seed (max 25 characters)"
                  : useEncryption 
                  ? "Encryption Key (max 25 characters)"
                  : "Randomization Seed (max 25 characters)"
                }
              </label>
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={key}
                    onChange={handleKeyChange}
                    maxLength={25}
                    placeholder={useEncryption && randomEmbedding 
                      ? "Enter key/seed (used for both encryption and randomization)"
                      : useEncryption 
                      ? "Enter your encryption key"
                      : "Enter your randomization seed"
                    }
                    className="block w-full px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500 focus:border-transparent text-sm"
                  />
                  <div className="absolute right-3 top-3 text-xs text-slate-400">
                    {key.length}/25
                  </div>
                </div>
                <Button
                  onClick={generateRandomKey}
                  variant="outline"
                  size="default"
                  className="px-4 py-3 border-slate-300 text-slate-700 hover:bg-slate-50"
                >
                  <Shuffle className="w-4 h-4 mr-2" />
                  Random
                </Button>
              </div>
              {useEncryption && randomEmbedding && (
                <div className="text-sm text-slate-600 bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <strong>Note:</strong> The same string will be used as both the encryption key and the randomization seed.
                </div>
              )}
            </div>
          )}

          {/* Embed Button */}
          <div className="flex justify-center pt-4">
            <Button
              onClick={handleEmbedFile}
              disabled={!selectedFile || !embedFile || ((useEncryption || randomEmbedding) && !key)}
              size="lg"
              className="px-8 py-3 bg-slate-700 hover:bg-slate-800 text-white font-medium disabled:bg-slate-300 disabled:cursor-not-allowed"
            >
              Embed File
            </Button>
          </div>

          {/* Output Section */}
          <div className="space-y-4 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Download className="w-4 h-4" />
              Output Result
            </label>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center">
              {outputFile ? (
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center">
                    <Download className="w-8 h-8 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      Steganography Completed
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      File: {outputFile.name}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4 border-slate-300 text-slate-700 hover:bg-slate-50"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download Result
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center mb-4">
                    <Download className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-sm">
                    Your processed file will appear here after embedding
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Secure audio steganography with encryption</p>
        </div>
      </div>
    </div>
  );
}

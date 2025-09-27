"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Key, Download, Shuffle, FileText, Lock, Unlock } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Decrypt() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState(null);
  const [key, setKey] = useState("");
  const [extractedFile, setExtractedFile] = useState(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === "audio/mpeg") {
      setSelectedFile(file);
    } else {
      alert("Please select an MP3 file");
      event.target.value = "";
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

  const handleExtractFile = () => {
    // This will be implemented when you add the API routes
    console.log("Extract file functionality to be implemented");
    console.log("Settings:", {
      mp3File: selectedFile?.name,
      key: key
    });
    // Simulating output for UI demonstration
    if (selectedFile && key) {
      // Create a mock extracted file for demonstration
      const mockFile = {
        name: "extracted_file.txt",
        size: 1024 * 5, // 5KB mock size
        type: "text/plain"
      };
      setExtractedFile(mockFile);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Audio Steganography Decrypt
          </h1>
          <p className="text-lg text-slate-600">
            Extract hidden files from MP3 audio files
          </p>
          
          {/* Navigation Buttons */}
          <div className="flex justify-center gap-4 mt-8">
            <Button
              onClick={() => router.push('/')}
              variant="outline"
              size="lg"
              className="px-6 py-2 border-slate-300 text-slate-700 hover:bg-slate-50"
            >
              <Lock className="w-4 h-4 mr-2" />
              Encrypt
            </Button>
            <Button
              disabled={true}
              size="lg"
              className="px-6 py-2 bg-slate-700 text-white font-medium disabled:bg-slate-400 disabled:cursor-not-allowed"
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
              Select MP3 File with Hidden Data
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

          {/* Key Input Section */}
          <div className="space-y-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Key className="w-4 h-4" />
              Decryption Key (max 25 characters)
            </label>
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={key}
                  onChange={handleKeyChange}
                  maxLength={25}
                  placeholder="Enter your decryption key"
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
          </div>

          {/* Extract Button */}
          <div className="flex justify-center pt-4">
            <Button
              onClick={handleExtractFile}
              disabled={!selectedFile || !key}
              size="lg"
              className="px-8 py-3 bg-slate-700 hover:bg-slate-800 text-white font-medium disabled:bg-slate-300 disabled:cursor-not-allowed"
            >
              Extract File
            </Button>
          </div>

          {/* Embedded File Output Section */}
          <div className="space-y-4 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <FileText className="w-4 h-4" />
              Embedded File
            </label>
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center">
              {extractedFile ? (
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center">
                    <FileText className="w-8 h-8 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      File Extracted Successfully
                    </p>
                    <p className="text-sm text-slate-500 mt-1">
                      File: {extractedFile.name}
                    </p>
                    <p className="text-sm text-slate-500">
                      Size: {(extractedFile.size / 1024).toFixed(2)} KB
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4 border-slate-300 text-slate-700 hover:bg-slate-50"
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download File
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-lg flex items-center justify-center mb-4">
                    <FileText className="w-8 h-8 text-slate-400" />
                  </div>
                  <p className="text-sm">
                    The extracted file will appear here after decryption
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Decrypt and extract hidden files from audio steganography</p>
        </div>
      </div>
    </div>
  );
}

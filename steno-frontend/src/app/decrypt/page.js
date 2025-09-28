"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, Key, Download, Shuffle, FileText, Settings } from "lucide-react";
import { useRouter } from "next/navigation";
import NavButton from "@/components/ui/navButton";

export default function Decrypt() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState(null);
  const [key, setKey] = useState("");
  const [extractedFile, setExtractedFile] = useState(null);
  const [useEncryption, setUseEncryption] = useState(true);
  const [lsbBits, setLsbBits] = useState(1);
  const [configuration, setConfiguration] = useState(null);
  const [extractedFileUrl, setExtractedFileUrl] = useState(null);
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

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

  const handleExtractFile = async () => {
    if (!selectedFile) return;

    try {
      const formData = new FormData();
      formData.append('mp3File', selectedFile);
      formData.append('useEncryption', useEncryption.toString());
      formData.append('lsbBits', lsbBits.toString());
      
      if (useEncryption && key) {
        formData.append('key', key);
      }

      console.log("Sending decrypt request...");
      
      const response = await fetch(`${backendUrl}/decrypt`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        console.log("Decrypt successful:", result);
        setConfiguration(result.configuration);
        
        if (result.extractedFileData) {
          try {
            const binaryString = atob(result.extractedFileData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            
            const fileBlob = new Blob([bytes], { type: result.mimeType || 'text/plain' });
            const fileUrl = URL.createObjectURL(fileBlob);
            
            setExtractedFile({
              name: result.extractedFileName,
              size: fileBlob.size,
              type: result.mimeType || 'text/plain'
            });
            setExtractedFileUrl(fileUrl);
          } catch (error) {
            console.error('Error processing extracted file data:', error);
            alert('Error processing extracted file: ' + error.message);
          }
        }
      } else {
        console.error("Decrypt failed:", result.error);
        alert(`Decryption failed: ${result.error}`);
      }
    } catch (error) {
      console.error("Error during decryption:", error);
      alert(`Error during decryption: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Audio Steganography Decrypt
          </h1>
          <p className="text-lg text-slate-600">
            Extract hidden files from MP3 audio files
          </p>
          
          <NavButton />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8 space-y-8">
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



          <div className="space-y-6 border-t border-slate-200 pt-6">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <Settings className="w-4 h-4" />
              Decryption Options
            </label>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
          </div>

          {useEncryption && (
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
          )}

          {/* Extract Button */}
          <div className="flex justify-center pt-4">
            <Button
              onClick={handleExtractFile}
              disabled={!selectedFile || (useEncryption && !key)}
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
                    
                    {configuration && (
                      <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-left">
                        <h4 className="text-sm font-semibold text-slate-900 mb-2">Configuration Used:</h4>
                        <div className="space-y-1 text-xs text-slate-600">
                          <div><strong>File Extension:</strong> {configuration.fileExtension}</div>
                          <div><strong>File Name:</strong> {configuration.fileName}</div>
                          <div><strong>Secret File Size:</strong> {configuration.secretFileSize}</div>
                          <div><strong>Use Encryption:</strong> {configuration.useEncryption ? 'Yes' : 'No'}</div>
                          <div><strong>Random Embed Point:</strong> {configuration.randomEmbedPoint ? 'Yes' : 'No'}</div>
                          <div><strong>LSB Bits:</strong> {configuration.lsbBits}-bit</div>
                        </div>
                      </div>
                    )}
                    
                    {extractedFileUrl && (
                      <Button
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = extractedFileUrl;
                          link.download = extractedFile.name || 'extracted_file.txt';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }}
                        variant="outline"
                        size="sm"
                        className="mt-4 border-slate-300 text-slate-700 hover:bg-slate-50"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download File
                      </Button>
                    )}
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

        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Decrypt and extract hidden files from audio steganography</p>
        </div>
      </div>
    </div>
  );
}
